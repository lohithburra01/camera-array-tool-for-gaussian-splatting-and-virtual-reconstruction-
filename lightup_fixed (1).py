bl_info = {
    "name": "Smart Lighting Setup",
    "author": "Your Name",
    "version": (1, 4),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Smart Lighting",
    "description": "Create scale-aware lighting setups with false color preview",
    "category": "Lighting",
}

import bpy
from mathutils import Vector
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty,
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
)

# Helper Functions
def get_object_dimensions(obj):
    """Get the dimensions of an object including all its children"""
    if obj is None or obj.name not in bpy.data.objects:
        return Vector((1, 1, 1))
    
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector((
        max(c.x for c in bbox_corners) - min(c.x for c in bbox_corners),
        max(c.y for c in bbox_corners) - min(c.y for c in bbox_corners),
        max(c.z for c in bbox_corners) - min(c.z for c in bbox_corners)
    ))

def calculate_light_distance(obj, factor=1.5):
    """Calculate light distance based on object dimensions"""
    if obj is None or obj.name not in bpy.data.objects:
        return 5.0
    return max(get_object_dimensions(obj)) * factor

def calculate_light_energy(distance, base_energy=100.0, falloff_factor=1.0):
    """Calculate light energy using modified inverse square law"""
    return base_energy * (1 + (distance * falloff_factor))

def setup_false_color(enable=True):
    """Toggle false color view transform with state management"""
    scene = bpy.context.scene
    if enable:
        if "prev_view_settings" not in scene:
            scene["prev_view_settings"] = {
                "view_transform": scene.view_settings.view_transform,
                "look": scene.view_settings.look
            }
        scene.view_settings.view_transform = 'False Color'
    else:
        if "prev_view_settings" in scene:
            scene.view_settings.view_transform = scene["prev_view_settings"]["view_transform"]
            scene.view_settings.look = scene["prev_view_settings"]["look"]
            del scene["prev_view_settings"]

def get_camera_direction():
    """Get camera/view direction vectors"""
    if bpy.context.scene.camera:
        cam = bpy.context.scene.camera
        return (
            cam.matrix_world.translation,
            -cam.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        )
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = next((s for s in area.spaces if s.type == 'VIEW_3D'), None)
            if space:
                view_matrix = space.region_3d.view_matrix.inverted()
                return (
                    view_matrix.translation,
                    -view_matrix.to_quaternion() @ Vector((0, 0, 1))
                )
    return (Vector((0, 0, 5)), Vector((0, 0, -1)))

def apply_light_settings(light, props, distance):
    """Apply common light settings with Blender 4.5 compatibility"""
    light.color = props.light_color
    light.shadow_soft_size = props.shadow_softness * distance * 0.1
    
    # Blender 4.5 compatible contact shadow settings
    if hasattr(light, 'use_contact_shadow'):
        light.use_contact_shadow = props.use_contact_shadows
        if props.use_contact_shadows:
            if hasattr(light, 'contact_shadow_distance'):
                light.contact_shadow_distance = distance * 0.1
            if hasattr(light, 'contact_shadow_thickness'):
                light.contact_shadow_thickness = distance * 0.02

# Property Group
class SmartLightingProperties(PropertyGroup):
    setup_type: EnumProperty(
        name="Setup Type",
        items=[
            ('THREE_POINT', "Three-Point", "Standard three-point lighting"),
            ('TWO_POINT', "Two-Point", "Two-point lighting setup"),
            ('SINGLE_POINT', "Single-Point", "Single light setup"),
            ('PRODUCT', "Product", "Product photography setup"),
            ('CINEMATIC', "Cinematic", "Dramatic cinematic lighting"),
            ('APPLE_STYLE', "Apple Style", "Apple-style edge highlights")
        ],
        default='THREE_POINT'
    )
    
    two_point_mode: EnumProperty(
        name="Mode",
        items=[
            ('FILL', "Fill Light", "Secondary fill light"),
            ('BACK', "Back Light", "Secondary back light")
        ],
        default='FILL'
    )
    
    single_point_mode: EnumProperty(
        name="Position",
        items=[
            ('STANDARD', "Standard", "Default key light position"),
            ('DRAMATIC', "Dramatic", "Extreme lighting angle"),
            ('OVERHEAD', "Overhead", "Top-down lighting")
        ],
        default='STANDARD'
    )
    
    light_color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0
    )
    
    base_energy: FloatProperty(
        name="Base Energy",
        default=100.0,
        min=1.0,
        max=1000.0
    )
    
    distance_factor: FloatProperty(
        name="Distance Factor",
        default=1.5,
        min=0.5,
        max=5.0
    )
    
    falloff_factor: FloatProperty(
        name="Falloff",
        default=1.0,
        min=0.1,
        max=5.0
    )
    
    shadow_softness: FloatProperty(
        name="Softness",
        default=1.0,
        min=0.1,
        max=10.0
    )
    
    use_contact_shadows: BoolProperty(
        name="Contact Shadows",
        default=True,
        description="Enable contact shadows (if supported)"
    )
    
    enable_false_color: BoolProperty(
        name="False Color",
        default=False
    )
    
    exposure_factor: FloatProperty(
        name="Exposure",
        default=1.0,
        min=0.1,
        max=10.0,
        subtype='FACTOR'
    )
    
    camera_follow: BoolProperty(
        name="Camera Follow",
        default=True
    )
    
    individual_light_control: BoolProperty(
        name="Individual Control",
        default=False
    )

# Operators
class LIGHTING_OT_create_setup(Operator):
    """Create lighting setup based on selected object"""
    bl_idname = "lighting.create_setup"
    bl_label = "Create Lighting Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.smart_lighting_props
        obj = context.active_object

        # Validate object
        if not obj or obj.name not in bpy.data.objects:
            self.report({'ERROR'}, "Select a valid object first")
            return {'CANCELLED'}

        # Calculate dimensions and distance
        distance = calculate_light_distance(obj, props.distance_factor)
        energy = calculate_light_energy(distance, props.base_energy, props.falloff_factor)

        # Create collection
        light_collection = bpy.data.collections.get("Smart_Lighting_Setup") or \
                         bpy.data.collections.new("Smart_Lighting_Setup")
        if not light_collection.users:
            bpy.context.scene.collection.children.link(light_collection)

        # Clear existing lights
        for ob in light_collection.objects:
            bpy.data.objects.remove(ob, do_unlink=True)

        # Get camera orientation
        cam_pos, cam_dir = get_camera_direction()
        cam_fwd = cam_dir.normalized()
        world_up = Vector((0, 0, 1))
        cam_right = cam_fwd.cross(world_up).normalized() if abs(cam_fwd.dot(world_up)) < 0.99 else Vector((1, 0, 0))
        cam_up = cam_right.cross(cam_fwd).normalized()
        obj_center = obj.matrix_world.translation

        # Full Three-Point Lighting Implementation
        if props.setup_type == 'THREE_POINT':
            # Key Light
            key_light = bpy.data.lights.new(name="Key_Light", type='AREA')
            key_light.energy = energy
            key_light.size = distance * 0.2
            key_light_obj = bpy.data.objects.new(name="Key_Light", object_data=key_light)
            key_light_obj.location = obj_center + cam_right * distance * 0.866 + cam_up * distance * 0.5 - cam_fwd * distance * 0.5
            direction = obj_center - key_light_obj.location
            key_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(key_light_obj)

            # Fill Light
            fill_light = bpy.data.lights.new(name="Fill_Light", type='AREA')
            fill_light.energy = energy * 0.5
            fill_light.size = distance * 0.3
            fill_light_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_light)
            fill_light_obj.location = obj_center - cam_right * distance * 0.866 + cam_up * distance * 0.3 - cam_fwd * distance * 0.5
            direction = obj_center - fill_light_obj.location
            fill_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(fill_light_obj)

            # Back Light
            back_light = bpy.data.lights.new(name="Back_Light", type='AREA')
            back_light.energy = energy * 0.75
            back_light.size = distance * 0.2
            back_light_obj = bpy.data.objects.new(name="Back_Light", object_data=back_light)
            back_light_obj.location = obj_center + cam_fwd * distance * 0.7 + cam_up * distance * 0.8
            direction = obj_center - back_light_obj.location
            back_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(back_light_obj)

        # Full Two-Point Lighting Implementation
        elif props.setup_type == 'TWO_POINT':
            # Key Light
            key_light = bpy.data.lights.new(name="Key_Light", type='AREA')
            key_light.energy = energy
            key_light.size = distance * 0.2
            key_light_obj = bpy.data.objects.new(name="Key_Light", object_data=key_light)
            key_light_obj.location = obj_center + cam_right * distance * 0.866 + cam_up * distance * 0.5 - cam_fwd * distance * 0.5
            direction = obj_center - key_light_obj.location
            key_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(key_light_obj)

            # Secondary Light
            if props.two_point_mode == 'FILL':
                sec_light = bpy.data.lights.new(name="Fill_Light", type='AREA')
                sec_light.energy = energy * 0.4
                sec_light.size = distance * 0.3
                sec_light_obj = bpy.data.objects.new(name="Fill_Light", object_data=sec_light)
                sec_light_obj.location = obj_center - cam_right * distance * 0.866 + cam_up * distance * 0.3 - cam_fwd * distance * 0.5
            else:
                sec_light = bpy.data.lights.new(name="Back_Light", type='AREA')
                sec_light.energy = energy * 0.6
                sec_light.size = distance * 0.2
                sec_light_obj = bpy.data.objects.new(name="Back_Light", object_data=sec_light)
                sec_light_obj.location = obj_center + cam_fwd * distance * 0.7 + cam_up * distance * 0.8
            
            direction = obj_center - sec_light_obj.location
            sec_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(sec_light_obj)

        # Full Single-Point Lighting Implementation
        elif props.setup_type == 'SINGLE_POINT':
            key_light = bpy.data.lights.new(name="Main_Light", type='AREA')
            key_light.energy = energy * 1.2
            key_light.size = distance * 0.3
            key_light_obj = bpy.data.objects.new(name="Main_Light", object_data=key_light)
            
            if props.single_point_mode == 'DRAMATIC':
                key_light_obj.location = obj_center + cam_right * distance * 0.966 + cam_up * distance * 0.7 - cam_fwd * distance * 0.3
            elif props.single_point_mode == 'OVERHEAD':
                key_light_obj.location = obj_center + cam_up * distance * 1.2
            else:
                key_light_obj.location = obj_center + cam_right * distance * 0.866 + cam_up * distance * 0.5 - cam_fwd * distance * 0.5
            
            direction = obj_center - key_light_obj.location
            key_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(key_light_obj)

        # Full Product Lighting Implementation
        elif props.setup_type == 'PRODUCT':
            # Top Light
            top_light = bpy.data.lights.new(name="Top_Light", type='AREA')
            top_light.energy = energy * 0.8
            top_light.size = distance * 0.5
            top_light_obj = bpy.data.objects.new(name="Top_Light", object_data=top_light)
            top_light_obj.location = obj_center + cam_up * distance * 1.0 - cam_fwd * distance * 0.2
            direction = obj_center - top_light_obj.location
            top_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(top_light_obj)

            # Front Light
            front_light = bpy.data.lights.new(name="Front_Light", type='AREA')
            front_light.energy = energy * 0.5
            front_light.size = distance * 0.6
            front_light_obj = bpy.data.objects.new(name="Front_Light", object_data=front_light)
            front_light_obj.location = obj_center - cam_fwd * distance * 1.0
            direction = obj_center - front_light_obj.location
            front_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(front_light_obj)

            # Side Lights
            for side in ['Right', 'Left']:
                light = bpy.data.lights.new(name=f"{side}_Light", type='AREA')
                light.energy = energy * (0.4 if side == 'Right' else 0.3)
                light.size = distance * 0.4
                light_obj = bpy.data.objects.new(name=f"{side}_Light", object_data=light)
                light_obj.location = obj_center + (cam_right if side == 'Right' else -cam_right) * distance
                direction = obj_center - light_obj.location
                light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
                light_collection.objects.link(light_obj)

        # Full Cinematic Lighting Implementation
        elif props.setup_type == 'CINEMATIC':
            # Key Light
            key_light = bpy.data.lights.new(name="Key_Light", type='AREA')
            key_light.energy = energy * 1.2
            key_light.size = distance * 0.4
            key_light.color = props.light_color
            key_light_obj = bpy.data.objects.new(name="Key_Light", object_data=key_light)
            key_light_obj.location = obj_center + cam_right * distance * 0.966 + cam_up * distance * 0.8 - cam_fwd * distance * 0.3
            direction = obj_center - key_light_obj.location
            key_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(key_light_obj)

            # Fill Light
            fill_light = bpy.data.lights.new(name="Fill_Light", type='AREA')
            fill_light.energy = energy * 0.15
            fill_light.size = distance * 0.6
            fill_light.color = props.light_color
            fill_light_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_light)
            fill_light_obj.location = obj_center - cam_right * distance * 0.8 - cam_fwd * distance * 0.5
            direction = obj_center - fill_light_obj.location
            fill_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(fill_light_obj)

            # Rim Light
            rim_light = bpy.data.lights.new(name="Rim_Light", type='AREA')
            rim_light.energy = energy * 0.9
            rim_light.size = distance * 0.25
            rim_light.color = props.light_color
            rim_light_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_light)
            rim_light_obj.location = obj_center + cam_fwd * distance * 0.8 + cam_up * distance * 0.5 - cam_right * distance * 0.3
            direction = obj_center - rim_light_obj.location
            rim_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(rim_light_obj)

        # Full Apple-Style Lighting Implementation
        elif props.setup_type == 'APPLE_STYLE':
            # Main Light
            main_light = bpy.data.lights.new(name="Main_Light", type='AREA')
            main_light.energy = energy * 0.6
            main_light.size = distance * 0.4
            main_light.color = props.light_color
            main_light_obj = bpy.data.objects.new(name="Main_Light", object_data=main_light)
            main_light_obj.location = obj_center + cam_right * distance * 0.5 + cam_up * distance * 0.5 - cam_fwd * distance * 0.7
            direction = obj_center - main_light_obj.location
            main_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            light_collection.objects.link(main_light_obj)

            # Edge Lights
            for i in [1, 2]:
                edge_light = bpy.data.lights.new(name=f"Edge_Light_{i}", type='AREA')
                edge_light.energy = energy * 1.5
                edge_light.size = distance * 0.1
                edge_light.color = (1.0, 1.0, 1.0)
                edge_light_obj = bpy.data.objects.new(name=f"Edge_Light_{i}", object_data=edge_light)
                if i == 1:
                    edge_light_obj.location = obj_center + cam_right * distance * 0.5 + cam_fwd * distance * 0.2 + cam_up * distance * 0.2
                else:
                    edge_light_obj.location = obj_center - cam_right * distance * 0.5 + cam_fwd * distance * 0.2 + cam_up * distance * 0.2
                direction = obj_center - edge_light_obj.location
                edge_light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
                light_collection.objects.link(edge_light_obj)

            # Fill and Back Lights
            for light_type in ['Fill', 'Back']:
                light = bpy.data.lights.new(name=f"{light_type}_Light", type='AREA')
                light.energy = energy * (0.3 if light_type == 'Fill' else 0.4)
                light.size = distance * (0.7 if light_type == 'Fill' else 0.2)
                light.color = props.light_color
                light_obj = bpy.data.objects.new(name=f"{light_type}_Light", object_data=light)
                if light_type == 'Fill':
                    light_obj.location = obj_center - cam_fwd * distance * 1.0
                else:
                    light_obj.location = obj_center + cam_fwd * distance * 0.8
                direction = obj_center - light_obj.location
                light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
                light_collection.objects.link(light_obj)

        # Apply common settings with compatibility check
        for light_obj in light_collection.objects:
            apply_light_settings(light_obj.data, props, distance)

        # Toggle false color
        setup_false_color(props.enable_false_color)

        return {'FINISHED'}

class LIGHTING_OT_toggle_false_color(Operator):
    """Toggle false color preview"""
    bl_idname = "lighting.toggle_false_color"
    bl_label = "Toggle False Color"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.smart_lighting_props
        setup_false_color(not props.enable_false_color)
        props.enable_false_color = not props.enable_false_color
        return {'FINISHED'}

class LIGHTING_OT_update_lights(Operator):
    """Update lighting parameters"""
    bl_idname = "lighting.update_lights"
    bl_label = "Update Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.smart_lighting_props
        light_collection = next((c for c in bpy.data.collections if "Smart_Lighting_Setup" in c.name), None)
        
        if not light_collection:
            self.report({'ERROR'}, "No lighting setup found")
            return {'CANCELLED'}
        
        obj = context.active_object
        distance = calculate_light_distance(obj, props.distance_factor) if obj else 5.0

        for light_obj in light_collection.objects:
            if light_obj.type == 'LIGHT':
                light = light_obj.data
                if not props.individual_light_control:
                    light.energy = calculate_light_energy(distance, props.base_energy, props.falloff_factor)
                    apply_light_settings(light, props, distance)
                else:
                    light.energy *= props.exposure_factor

        props.exposure_factor = 1.0  # Reset exposure
        return {'FINISHED'}

class LIGHTING_OT_adjust_exposure(Operator):
    """Adjust exposure multiplier"""
    bl_idname = "lighting.adjust_exposure"
    bl_label = "Adjust Exposure"
    bl_options = {'REGISTER', 'UNDO'}
    
    exposure_factor: FloatProperty(
        name="Factor",
        default=1.0,
        min=0.1,
        max=10.0
    )

    def execute(self, context):
        context.scene.smart_lighting_props.exposure_factor = self.exposure_factor
        bpy.ops.lighting.update_lights()
        return {'FINISHED'}
    
class LIGHTING_PT_smart_lighting_panel(Panel):
    """Smart Lighting Setup Panel"""
    bl_label = "Smart Lighting Setup"
    bl_idname = "LIGHTING_PT_smart_lighting"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Smart Lighting"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.smart_lighting_props
        
        # Creation Section - Preserved Original Layout
        box = layout.box()
        box.label(text="Create Lighting Setup")
        box.prop(props, "setup_type")
        
        if props.setup_type == 'TWO_POINT':
            box.prop(props, "two_point_mode")
        elif props.setup_type == 'SINGLE_POINT':
            box.prop(props, "single_point_mode")
        
        box.prop(props, "camera_follow", icon='HIDE_OFF')
        box.operator("lighting.create_setup")

        # Global Properties - Original Structure Maintained
        has_lights = any("Smart_Lighting_Setup" in c.name for c in bpy.data.collections)
        if has_lights:
            box = layout.box()
            box.label(text="Global Light Properties")
            box.prop(props, "individual_light_control")
            
            if not props.individual_light_control:
                box.prop(props, "light_color")
                box.prop(props, "base_energy")
                box.prop(props, "shadow_softness")
                box.prop(props, "use_contact_shadows")
                
                box = layout.box()
                box.label(text="Scale Settings")
                box.prop(props, "distance_factor")
                box.prop(props, "falloff_factor")
                
                box.operator("lighting.update_lights")
            
            # Exposure Control - Original Layout
            box = layout.box()
            box.label(text="Exposure Adjustment")
            box.prop(props, "exposure_factor", slider=True)
            box.operator("lighting.update_lights", text="Apply Exposure Change")
            
            # False Color Toggle - Original Button Style
            row = layout.row()
            row.operator("lighting.toggle_false_color", 
                         text="Disable False Color" if props.enable_false_color else "Enable False Color")
        else:
            # Initial Settings - Preserved Original
            box = layout.box()
            box.label(text="Light Properties")
            box.prop(props, "light_color")
            box.prop(props, "base_energy")
            box.prop(props, "shadow_softness")
            box.prop(props, "use_contact_shadows")
            
            box = layout.box()
            box.label(text="Scale Settings")
            box.prop(props, "distance_factor")
            box.prop(props, "falloff_factor")

# Preserve Original Handler Logic with Validation Fixes
@bpy.app.handlers.persistent
def camera_update_handler(scene):
    if not hasattr(scene, "smart_lighting_props") or not scene.smart_lighting_props.camera_follow:
        return
    
    # Original Positioning Logic with Object Validation
    light_collection = next((c for c in bpy.data.collections if "Smart_Lighting_Setup" in c.name), None)
    if not light_collection or not light_collection.objects:
        return
    
    obj = bpy.context.active_object
    if not obj or obj.name not in bpy.data.objects:
        return
    
    # Keep Original Coordinate Calculations
    obj_center = obj.matrix_world.translation
    cam_pos, cam_dir = get_camera_direction()
    cam_fwd = cam_dir.normalized()
    world_up = Vector((0, 0, 1))
    
    if abs(cam_fwd.dot(world_up)) > 0.99:
        cam_right = Vector((1, 0, 0))
    else:
        cam_right = cam_fwd.cross(world_up).normalized()
    
    cam_up = cam_right.cross(cam_fwd).normalized()
    distance = calculate_light_distance(obj, scene.smart_lighting_props.distance_factor)

    # Original Light Positioning Rules
    for light_obj in light_collection.objects:
        if light_obj.type != 'LIGHT':
            continue
            
        light_name = light_obj.name
        new_pos = obj_center.copy()
        
        if "Key_Light" in light_name:
            new_pos += cam_right * distance * 0.866 + cam_up * distance * 0.5 - cam_fwd * distance * 0.5
        elif "Fill_Light" in light_name:
            new_pos += -cam_right * distance * 0.866 + cam_up * distance * 0.3 - cam_fwd * distance * 0.5
        elif "Back_Light" in light_name or "Rim_Light" in light_name:
            new_pos += cam_fwd * distance * 0.7 + cam_up * distance * 0.8
        elif "Top_Light" in light_name:
            new_pos += cam_up * distance * 1.0 - cam_fwd * distance * 0.2
        elif "Front_Light" in light_name:
            new_pos += -cam_fwd * distance * 1.0
        elif "Right_Light" in light_name:
            new_pos += cam_right * distance * 1.0
        elif "Left_Light" in light_name:
            new_pos += -cam_right * distance * 1.0
        elif "Main_Light" in light_name:
            new_pos += cam_right * distance * 0.866 + cam_up * distance * 0.5 - cam_fwd * distance * 0.5
        elif "Edge_Light" in light_name:
            new_pos += cam_fwd * distance * 0.3 + cam_up * distance * 0.5
            
        light_obj.location = new_pos
        direction = obj_center - new_pos
        light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def register():
    # Original Registration with Handler Fix
    bpy.utils.register_class(SmartLightingProperties)
    bpy.utils.register_class(LIGHTING_OT_create_setup)
    bpy.utils.register_class(LIGHTING_OT_toggle_false_color)
    bpy.utils.register_class(LIGHTING_OT_adjust_exposure)
    bpy.utils.register_class(LIGHTING_OT_update_lights)
    bpy.utils.register_class(LIGHTING_PT_smart_lighting_panel)
    
    # Safe Handler Registration
    if camera_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(camera_update_handler)
    bpy.app.handlers.depsgraph_update_post.append(camera_update_handler)
    
    bpy.types.Scene.smart_lighting_props = PointerProperty(type=SmartLightingProperties)

def unregister():
    # Original Unregistration with Handler Cleanup
    if camera_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(camera_update_handler)
    
    del bpy.types.Scene.smart_lighting_props
    bpy.utils.unregister_class(LIGHTING_PT_smart_lighting_panel)
    bpy.utils.unregister_class(LIGHTING_OT_update_lights)
    bpy.utils.unregister_class(LIGHTING_OT_adjust_exposure)
    bpy.utils.unregister_class(LIGHTING_OT_toggle_false_color)
    bpy.utils.unregister_class(LIGHTING_OT_create_setup)
    bpy.utils.unregister_class(SmartLightingProperties)

if __name__ == "__main__":
    register()