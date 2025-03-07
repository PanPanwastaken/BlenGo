###############################
#    Created by PanPan
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################

bl_info = {
    "name": "BlenGo",
    "author": "PanPan",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > BlenGo",
    "description": "A toolset for Blender/Godot pipelines",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export",
}

###############################
# Imports
###############################

import bpy
from mathutils import Vector
from bpy.props import (
    StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty
)
import os, re, shutil
from bpy_extras.io_utils import ImportHelper
import random, string

###############################
# Update Custom property values 
###############################

#for object properties

def update_obj_prop(self, context):
    obj = bpy.context.active_object
    if obj:
        if self.prop_selection in {"CastShadowOn", "CastShadowOff"}:
            final_val = self.prop_selection
        elif self.prop_selection == "Script":
            prefix = "scriptpath:"
            final_val = prefix + self.prop_raw
        else:  # Custom
            final_val = self.prop_raw

        obj[self.prop_name] = final_val
        if "_RNA_UI" not in obj:
            obj["_RNA_UI"] = {}
        obj["_RNA_UI"][self.prop_name] = {"description": final_val}


##############################

#for mesh properties
def update_mesh_prop_selection(self, context):
    if self.prop_selection != "Custom":
        self.prop_description = self.prop_selection

###############################
# Update callback for material property description
###############################

def update_prop_desc(self, context):
    obj = bpy.context.active_object
    if obj and obj.active_material:
        mat = obj.active_material
        mat[self.prop_name] = self.prop_description
        if "_RNA_UI" not in mat:
            mat["_RNA_UI"] = {}
        mat["_RNA_UI"][self.prop_name] = {"description": self.prop_description}

###############################
# Update callback for object property description
###############################

def update_obj_prop_desc(self, context):
    obj = bpy.context.active_object
    if obj:
        obj[self.prop_name] = self.prop_description
        if "_RNA_UI" not in obj:
            obj["_RNA_UI"] = {}
        obj["_RNA_UI"][self.prop_name] = {"description": self.prop_description}

###############################
# Update callback for Mesh property description
###############################

def update_godot_mesh_prop_desc(self, context):
    obj = bpy.context.active_object
    if obj and obj.data and hasattr(obj.data, "godot_mesh_properties"):
        mesh = obj.data
        mesh[self.prop_name] = self.prop_description
        if "_RNA_UI" not in mesh:
            mesh["_RNA_UI"] = {}
        mesh["_RNA_UI"][self.prop_name] = {"description": self.prop_description}

###############################
# Property Group: Godot Material Property
###############################

class GodotMaterialProperty(bpy.types.PropertyGroup):
    prop_name: StringProperty(
        name="Property Name",
        description="This is automatically set from the active material slot"
    )
    prop_description: StringProperty(
        name="Godot path:",
        default="",
        description="Custom Godot path for this material property (for Godot import script)",
        update=update_prop_desc
    )

###############################
# Property Group: Godot Object Property
###############################

class GodotObjectProperty(bpy.types.PropertyGroup):
    prop_name: StringProperty(
        name="Property Name",
        description="Automatically set from the active object"
    )
    prop_selection: EnumProperty(
        name="Option",
        description="Select a predefined option, Script, or Custom for manual entry",
        items=[
            ("CastShadowOn", "CastShadowOn", "Enable cast shadow"),
            ("CastShadowOff", "CastShadowOff", "Disable cast shadow"),
            ("Script", "Script", "Assign a script path"),
            ("Custom", "Custom", "Enter custom value")
        ],
        default="Custom",
        update=update_obj_prop
    )
    # This property stores the user-entered text.
    prop_raw: StringProperty(
        name="Godot path:",
        default="",
        description="User entered text",
        update=update_obj_prop
    )

###############################
    def get_prop_description(self):
        if self.prop_selection == "Script":
            return "scriptpath:" + self.prop_raw
        else:
            return self.prop_raw

    def set_prop_description(self, value):
        if self.prop_selection == "Script":
            prefix = "scriptpath:"
            if value.startswith(prefix):
                self.prop_raw = value[len(prefix):]
            else:
                self.prop_raw = value
        else:
            self.prop_raw = value

    prop_description: StringProperty(
        name="Godot path:",
        get=get_prop_description,
        set=set_prop_description,
        description="Custom Godot path for this object property (for Godot Import script)"
    )

###############################
# Property Group: Godot Mesh Property (for meshes)
###############################

class GodotMeshProperty(bpy.types.PropertyGroup):
    prop_name: bpy.props.StringProperty(
        name="Property Name",
        description="This is automatically set from the active mesh"
    )
    #enum property for mesh properties with a 'Custom' option.
    prop_selection: EnumProperty(
        name="Option",
        description="Select a predefined option or Custom for manual entry",
        items=[
            ("LightMapOn", "LightMapOn", "Enable light map"),
            ("LightMapOff", "LightMapOff", "Disable light map"),
            ("ShadowMeshesOn", "ShadowMeshesOn", "Enable shadow meshes"),
            ("ShadowMeshesOff", "ShadowMeshesOff", "Disable shadow meshes"),
            ("Custom", "Custom", "Enter custom value")
        ],
        default="Custom",
        update=update_mesh_prop_selection
    )
    prop_description: bpy.props.StringProperty(
        name="Godot path:",
        default="",
        description="Custom Godot path for this mesh property (for Godot import script)",
        update=update_godot_mesh_prop_desc
    )

###############################
# Feature: Fix Root Bone Rotations
###############################

def add_root_bone_and_copy_animation(armature, hip_bone_name, root_bone_name):
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = armature.data.edit_bones
    if root_bone_name in edit_bones:
        print(f"{root_bone_name} already exists in {armature.name}")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    
    if hip_bone_name not in edit_bones:
        print(f"{hip_bone_name} not found in {armature.name}")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    
    hips_bone = edit_bones[hip_bone_name]
    
    # Duplicate hip bone and rename to root bone
    root_bone = edit_bones.new(root_bone_name)
    root_bone.head = hips_bone.head.copy()
    root_bone.tail = hips_bone.tail.copy()
    root_bone.roll = hips_bone.roll
    
    hips_bone.parent = root_bone
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Copy keyframes from hip bone to root bone
    action = armature.animation_data.action if armature.animation_data else None
    if not action:
        print(f"No animation found in {armature.name}")
        return
    
    new_action = action.copy()
    new_action.name = f"{action.name}_root"
    armature.animation_data.action = new_action
    
    existing_paths = set()
    
    for fcurve in list(action.fcurves):
        data_path = fcurve.data_path
        key = f'pose.bones["{hip_bone_name}"].location'
        if data_path.startswith(key):
            new_data_path = data_path.replace(hip_bone_name, root_bone_name)
            if (new_data_path, fcurve.array_index) not in existing_paths:
                existing_paths.add((new_data_path, fcurve.array_index))
                new_fcurve = new_action.fcurves.new(
                    data_path=new_data_path,
                    index=fcurve.array_index,
                    action_group=root_bone_name
                )
                new_fcurve.keyframe_points.add(len(fcurve.keyframe_points))
                for i, kfp in enumerate(fcurve.keyframe_points):
                    new_fcurve.keyframe_points[i].co = kfp.co
                    new_fcurve.keyframe_points[i].interpolation = kfp.interpolation
    
    print(f'F-Curves containing "pose.bones[\"{hip_bone_name}\"].location":')
    for fcurve in new_action.fcurves:
        if f'pose.bones["{hip_bone_name}"].location' in fcurve.data_path:
            print(f" - {fcurve.data_path} [Index: {fcurve.array_index}]")
    
    for fcurve in list(new_action.fcurves):
        if fcurve.data_path.startswith(f'pose.bones["{hip_bone_name}"].location'):
            new_action.fcurves.remove(fcurve)
    
    bpy.ops.object.mode_set(mode='POSE')
    hip_pose = armature.pose.bones.get(hip_bone_name)
    if hip_pose:
        hip_pose.location = (0.0, 0.0, 0.0)
    
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Successfully duplicated {hip_bone_name} as {root_bone_name} for {armature.name}")

class OBJECT_OT_godot_tools(bpy.types.Operator):
    """Add a new root bone to handle mocap movement root without any rotations,
    while the old root bone handles rotations (for rigs like Mixamo)"""
    bl_idname = "object.godot_tools"
    bl_label = "BlenGo"
    bl_options = {'REGISTER', 'UNDO'}
    
    hip_bone_name: StringProperty(
        name="Hip Bone Name",
        default="mixamorig:Hips",
        description="Name of existing hip bone (old root bone)"
    )
    root_bone_name: StringProperty(
        name="Root Bone Name",
        default="root_bone",
        description="Name of the new root bone"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        if not selected_armatures:
            self.report({'WARNING'}, "No armatures selected.")
            return {'CANCELLED'}
        for armature in selected_armatures:
            add_root_bone_and_copy_animation(armature, self.hip_bone_name, self.root_bone_name)
        return {'FINISHED'}

###############################
# Feature: Suffix Tools 
###############################

class OBJECT_OT_suffix_tools_add(bpy.types.Operator):
    """Add the selected suffix to the object's name"""
    bl_idname = "object.suffix_tools_add"
    bl_label = "Add Suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        suffix = context.scene.godot_suffix
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}
        for obj in selected_objects:
            if suffix not in obj.name:
                obj.name += suffix
        self.report({'INFO'}, f"Added '{suffix}' to object names.")
        return {'FINISHED'}

class OBJECT_OT_suffix_tools_remove(bpy.types.Operator):
    """Remove the selected suffix from the object's name"""
    bl_idname = "object.suffix_tools_remove"
    bl_label = "Remove Suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        suffix = context.scene.godot_suffix
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}
        for obj in selected_objects:
            if suffix in obj.name:
                obj.name = obj.name.replace(suffix, "")
        self.report({'INFO'}, f"Removed '{suffix}' from object names.")
        return {'FINISHED'}

def get_suffix_description(suffix):
    descriptions = {
        "-navmesh": "Suffix '-navmesh' is used for navigation mesh objects.",
        "-occ": "Suffix '-occ' indicates occlusion objects.",
        "-rigid": "Suffix '-rigid' is used for rigid body objects.",
        "-cycle": "Suffix '-cycle' relates to cyclic animations or cycles.",
        "-vehicle": "Suffix '-vehicle' is designated for vehicle objects.",
        "-wheel": "Suffix '-wheel' is used for wheel objects.",
        "-col": "Suffix '-col' marks collision objects.",
        "-convcol": "Suffix '-convcol' is for convex collision objects.",
        "-colonly": "Suffix '-colonly' is used for collision-only objects.",
        "-convcolonly": "Suffix '-convcolonly' is for convex collision-only objects.",
    }
    return descriptions.get(suffix, "No description available for this suffix.")

###############################
# Feature: Add Collision for Selected Objects
###############################
class OBJECT_OT_add_collision(bpy.types.Operator):
    """Add a collision object to each selected object."""
    bl_idname = "object.add_collision"
    bl_label = "Add Collision Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collision_shape = context.scene.godot_collision_shape
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}
        for obj in selected_objects:
            if collision_shape == 'CUBE':
                bpy.ops.mesh.primitive_cube_add(location=obj.location, rotation=obj.rotation_euler)
            elif collision_shape == 'CYLINDER':
                bpy.ops.mesh.primitive_cylinder_add(vertices=5, location=obj.location, rotation=obj.rotation_euler)
            collision_obj = context.active_object
            collision_obj.name = f"{obj.name}-colonly"
            collision_obj.parent = obj
            collision_obj.location = (0.0, 0.0, 0.0)
            collision_obj.rotation_euler = (0.0, 0.0, 0.0)
            collision_obj.display_type = 'WIRE'
        self.report({'INFO'}, "Added collision objects for selected objects.")
        return {'FINISHED'}
###############################
# Feature: Asset Folder Path and Export Textures
###############################
class OBJECT_OT_set_asset_folder_path(bpy.types.Operator, ImportHelper):
    """Set the asset folder path for the Godot project by picking a folder. (thie function will create a folder based on the name of blendfile and subfolders for textures, materials and scene) """
    bl_idname = "object.set_asset_folder_path"
    bl_label = "Set Assets Folder"
    bl_options = {'REGISTER', 'UNDO'}

    # Tweak ImportHelper to allow picking folders
    filename_ext = ""  # no file extension
    use_filter_folder = True
    filter_glob: StringProperty(default="", options={'HIDDEN'})

    def draw(self, context):
        # Overriding draw() with nothing hides the side-panel properties
        pass

    def invoke(self, context, event):
        # open file browser to open in "directory" mode.
        self.filemode = 2
        return super().invoke(context, event)

    def execute(self, context):
        # The user-picked folder path is in self.filepath
        project_folder = os.path.dirname(self.filepath)
        print("Selected folder:", project_folder)

        if not os.path.isdir(project_folder):
            self.report({'ERROR'}, f"Invalid folder path: {project_folder}")
            return {'CANCELLED'}

        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Please save the blend file first.")
            return {'CANCELLED'}

        blend_name = os.path.splitext(os.path.basename(blend_file))[0]
        asset_path = os.path.join(project_folder, blend_name)
        asset_path = os.path.abspath(asset_path)

        # Remove existing asset folder if it exists
        if os.path.exists(asset_path):
            try:
                shutil.rmtree(asset_path)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to remove existing asset folder: {e}")
                return {'CANCELLED'}

        os.makedirs(asset_path)

        # Create subfolders
        scene_folder = os.path.join(asset_path, "scene")
        textures_folder = os.path.join(asset_path, "textures")
        materials_folder = os.path.join(asset_path, "materials")

        for folder in [scene_folder, textures_folder, materials_folder]:
            os.makedirs(folder, exist_ok=True)

        # Store paths in the Scene properties
        scene = context.scene
        scene.godot_asset_asset_path = asset_path
        scene.godot_asset_scene_path = scene_folder
        scene.godot_asset_textures_path = textures_folder
        scene.godot_asset_materials_path = materials_folder

        self.report({'INFO'}, "Asset folders created and saved")
        return {'FINISHED'}

    def invoke(self, context, event):
        scene = context.scene
        # If an asset folder is already set, use it as the default folder.
        if scene.godot_asset_asset_path:
            self.asset_folder = os.path.dirname(scene.godot_asset_asset_path)
        elif bpy.data.filepath:
            self.asset_folder = os.path.dirname(bpy.data.filepath)
        else:
            self.asset_folder = os.path.expanduser("~")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class OBJECT_OT_export_textures(bpy.types.Operator):
    """Export all textures used in the blend file to the textures folder.
Existing files will be overwritten."""
    bl_idname = "object.export_textures"
    bl_label = "Export Textures"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        textures_folder = scene.godot_asset_textures_path
        if not textures_folder or not os.path.isdir(textures_folder):
            self.report({'ERROR'}, "Textures folder not set or invalid. Please set asset folder path first.")
            return {'CANCELLED'}
        
        rescale = scene.godot_texture_rescale
        resolution = int(scene.godot_texture_resolution) if rescale else None
        
        exported = 0
        for img in bpy.data.images:
            if img.users > 0 and (img.filepath or img.packed_file):
                if img.filepath:
                    filename = os.path.basename(img.filepath)
                else:
                    filename = img.name + ".png"
                out_filepath = os.path.join(textures_folder, filename)
                try:
                    if rescale and resolution:
                        # Make a copy of the image, scale it, save, and remove the copy.
                        new_img = img.copy()
                        new_img.scale(resolution, resolution)
                        new_img.file_format = 'PNG'
                        new_img.save_render(out_filepath)
                        bpy.data.images.remove(new_img)
                    else:
                        img.file_format = 'PNG'
                        img.save_render(out_filepath)
                    exported += 1
                except Exception as e:
                    self.report({'WARNING'}, f"Could not export {img.name}: {str(e)}")
        self.report({'INFO'}, f"Exported {exported} texture(s) to {textures_folder}")
        return {'FINISHED'}

###############################
# New Feature: Export GLTF
###############################
class OBJECT_OT_export_gltf_fixed(bpy.types.Operator):
    """Export the scene to GLTF using the preset scene folder.
The output filepath is prefilled (using the /scene subfolder of the asset folder and the blend file name).
Please do not change the file path in the file browser."""
    bl_idname = "object.export_gltf_fixed"
    bl_label = "Export GLTF (Fixed Path)"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        scene = context.scene
        if not scene.godot_asset_scene_path or not os.path.isdir(scene.godot_asset_scene_path):
            self.report({'ERROR'}, "Scene folder not set or invalid. Please set asset folder path first.")
            return {'CANCELLED'}
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Please save the blend file first.")
            return {'CANCELLED'}
        blend_name = os.path.splitext(os.path.basename(blend_file))[0]
        self.filepath = os.path.join(scene.godot_asset_scene_path, blend_name + ".gltf")
        print("Preset filepath:", self.filepath)  # Debug output
        return bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath=self.filepath)

    def execute(self, context):
        return {'FINISHED'}

###############################
# Feature: Custom Material Properties (for active material)
###############################

class OBJECT_OT_add_material_property(bpy.types.Operator):
    """Add a new custom material property to the active material.
The property name will be 'Material: ' + active material name,
and its 'Godot path:' can be edited directly in the UI."""
    bl_idname = "object.add_material_property"
    bl_label = "Add Material Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        if not obj.material_slots:
            self.report({'WARNING'}, "Active object has no material slots.")
            return {'CANCELLED'}
        idx = obj.active_material_index
        if idx < 0 or idx >= len(obj.material_slots):
            self.report({'WARNING'}, "Invalid active material slot.")
            return {'CANCELLED'}
        slot = obj.material_slots[idx]
        if not slot or not slot.material:
            self.report({'WARNING'}, "Active material slot has no material.")
            return {'CANCELLED'}
        mat = slot.material
        prop_name = "Material: " + mat.name
        mat[prop_name] = ""
        if "_RNA_UI" not in mat:
            mat["_RNA_UI"] = {}
        mat["_RNA_UI"][prop_name] = {"description": ""}
        new_item = mat.godot_material_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        self.report({'INFO'}, f"Added custom material property '{prop_name}'.")
        return {'FINISHED'}

###############################
# Operator: Delete Material Property
###############################

class OBJECT_OT_delete_material_property(bpy.types.Operator):
    """Delete a custom material property from the active material."""
    bl_idname = "object.delete_material_property"
    bl_label = "Delete Material Property"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.material_slots or not obj.active_material:
            self.report({'WARNING'}, "No active material found.")
            return {'CANCELLED'}
        mat = obj.material_slots[obj.active_material_index].material
        try:
            mat.godot_material_properties.remove(self.index)
            prop = "Material: " + mat.name
            if prop in mat:
                del mat[prop]
            if "_RNA_UI" in mat and prop in mat["_RNA_UI"]:
                del mat["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted material property.")
        return {'FINISHED'}

###############################
# Feature: Add Object Properties (for active object)
###############################

class OBJECT_OT_add_object_property(bpy.types.Operator):
    """Add a new custom object property to the active object."""
    bl_idname = "object.add_object_property"
    bl_label = "Add Object Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        prop_name = "Object: " + obj.name
        obj[prop_name] = ""
        if "_RNA_UI" not in obj:
            obj["_RNA_UI"] = {}
        obj["_RNA_UI"][prop_name] = {"description": ""}
        new_item = obj.godot_object_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        # Set the default selection to "Custom"
        new_item.prop_selection = "Custom"
        self.report({'INFO'}, f"Added custom object property '{prop_name}'.")
        return {'FINISHED'}

###############################
# Operator: Delete Object Property
###############################

class OBJECT_OT_delete_object_property(bpy.types.Operator):
    """Delete a custom object property from the active object."""
    bl_idname = "object.delete_object_property"
    bl_label = "Delete Object Property"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        try:
            obj.godot_object_properties.remove(self.index)
            prop = "Object: " + obj.name
            if prop in obj:
                del obj[prop]
            if "_RNA_UI" in obj and prop in obj["_RNA_UI"]:
                del obj["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted object property.")
        return {'FINISHED'}


###############################
# Operator: Add Godot Mesh Property
###############################

class OBJECT_OT_add_godot_mesh_property(bpy.types.Operator):
    """Add a new custom mesh property to the active mesh.
The property name will be 'Mesh: ' + active mesh name,
and effects all instances unlike Object Properties."""
    bl_idname = "object.add_godot_mesh_property"
    bl_label = "Add Godot Mesh Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh found.")
            return {'CANCELLED'}
        mesh = obj.data
        prop_name = "Mesh: " + mesh.name
        mesh[prop_name] = ""
        if "_RNA_UI" not in mesh:
            mesh["_RNA_UI"] = {}
        mesh["_RNA_UI"][prop_name] = {"description": ""}
        new_item = mesh.godot_mesh_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        new_item.prop_selection = "Custom"
        self.report({'INFO'}, f"Added custom Godot mesh property '{prop_name}'.")
        return {'FINISHED'}

###############################
# Operator: Delete Godot Mesh Property
###############################

class OBJECT_OT_delete_godot_mesh_property(bpy.types.Operator):
    """Delete a custom Godot mesh property from the active mesh."""
    bl_idname = "object.delete_godot_mesh_property"
    bl_label = "Delete Godot Mesh Property"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh found.")
            return {'CANCELLED'}
        mesh = obj.data
        try:
            mesh.godot_mesh_properties.remove(self.index)
            prop = "Mesh: " + mesh.name
            if prop in mesh:
                del mesh[prop]
            if "_RNA_UI" in mesh and prop in mesh["_RNA_UI"]:
                del mesh["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted Godot mesh property.")
        return {'FINISHED'}

###############################
# Feature: init Suffix Tools
###############################

def init_suffix_properties():
    bpy.types.Scene.godot_suffix_tools_collapsible = BoolProperty(
        name="Suffix Tools",
        default=True,
        description="Add suffixes recognized by Godot engine for various actions"
    )
    bpy.types.Scene.godot_suffix = EnumProperty(
        name="Suffix",
        description="Select the suffix to work with",
        items=[
            ("-navmesh", "-navmesh", "Suffix for navigation meshes"),
            ("-occ", "-occ", "Suffix for occlusion objects"),
            ("-rigid", "-rigid", "Suffix for rigid bodies"),
            ("-cycle", "-cycle", "Suffix for cyclic animations"),
            ("-vehicle", "-vehicle", "Suffix for vehicles"),
            ("-wheel", "-wheel", "Suffix for wheels"),
            ("-col", "-col", "Suffix for collision objects"),
            ("-convcol", "-convcol", "Suffix for convex collisions"),
            ("-colonly", "-colonly", "Suffix for collision-only objects"),
            ("-convcolonly", "-convcolonly", "Suffix for convex collision-only objects")
        ],
        default="-rigid"
    )


    
###############################
# Feature: Collision Tools
###############################

    bpy.types.Scene.godot_collision_tools_collapsible = BoolProperty(
        name="Add Collision for Selected Objects",
        default=True,
        description="Show collision tools for adding a collision object to selected objects"
    )
    bpy.types.Scene.godot_collision_shape = EnumProperty(
        name="Shape:",
        description="Choose the shape of the collision object",
        items=[
            ("CUBE", "Cube", "Cube"),
            ("CYLINDER", "Cylinder", "Cylinder (5 vertices)")
        ],
        default="CUBE"
    )
    
###############################
# Feature: Asset Path
###############################

    bpy.types.Scene.godot_asset_data_collapsible = BoolProperty(
        name="Asset Folder Path",
        default=True,
        description="Set asset folder path and create asset subfolders for the blend file"
    )
    # texture rescaling options
    bpy.types.Scene.godot_texture_rescale = BoolProperty(
        name="Rescale Textures",
        default=False,
        description="Export textures scaled to the chosen resolution"
    )
    bpy.types.Scene.godot_texture_resolution = EnumProperty(
        name="Texture Resolution",
        items=[
            ("1024", "1K", "Export textures at 1K resolution"),
            ("2048", "2K", "Export textures at 2K resolution"),
            ("4096", "4K", "Export textures at 4K resolution")
        ],
        default="1024"
    )
    # Asset folder path properties
    bpy.types.Scene.godot_asset_asset_path = StringProperty(
        name="Asset Folder",
        description="Asset folder for this blend file",
        default=""
    )
    bpy.types.Scene.godot_asset_scene_path = StringProperty(
        name="Scene Folder",
        description="Scene subfolder path",
        default=""
    )
    bpy.types.Scene.godot_asset_textures_path = StringProperty(
        name="Textures Folder",
        description="Textures subfolder path",
        default=""
    )
    bpy.types.Scene.godot_asset_materials_path = StringProperty(
        name="Materials Folder",
        description="Materials subfolder path",
        default=""
    )

###############################
# Custom Properies Collection
###############################

    # Custom Material Properties Collection on Material
    bpy.types.Material.godot_material_properties = CollectionProperty(type=GodotMaterialProperty)
    bpy.types.Material.godot_material_properties_index = IntProperty(name="Index", default=0)
    # Custom Object Properties Collection on Object
    bpy.types.Object.godot_object_properties = CollectionProperty(type=GodotObjectProperty)
    bpy.types.Object.godot_object_properties_index = IntProperty(name="Index", default=0)
    # Custom Mesh Properties Collection on Object
    bpy.types.Mesh.godot_mesh_properties = bpy.props.CollectionProperty(type=GodotMeshProperty)
    bpy.types.Mesh.godot_mesh_properties_index = bpy.props.IntProperty(name="Index", default=0)

###############################
# feature: material generator
###############################


def init_godot_root_project():
    bpy.types.Scene.godot_project_root = StringProperty(
        name="Godot Project Root",
        description="The root folder of your Godot project (this folder corresponds to res://)",
        default="",
        subtype='DIR_PATH'
    )



class OBJECT_OT_set_project_root(bpy.types.Operator, ImportHelper):
    """Set the Godot project root path (corresponds to res://)"""
    bl_idname = "object.set_project_root"
    bl_label = "Set Godot Project Root"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ""  # No extension
    use_filter_folder = True
    filter_glob: StringProperty(default="", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filemode = 2  # Directory mode
        return super().invoke(context, event)

    def execute(self, context):
        # Here, self.filepath contains the selected directory
        project_root = os.path.abspath(self.filepath)
        context.scene.godot_project_root = project_root
        print("Godot project root set to:", project_root)
        self.report({'INFO'}, f"Godot project root set to: {project_root}")
        return {'FINISHED'}

def compute_godot_relative_path(target_path, project_root):
    """
    Given a target file path and the Godot project root,
    compute the relative path as Godot expects, i.e. starting with "res://".
    """
    target_path = os.path.abspath(target_path)
    project_root = os.path.abspath(project_root)
    rel_path = os.path.relpath(target_path, project_root)
    return "res://" + rel_path.replace("\\", "/")
###############################################
class OBJECT_OT_export_materials(bpy.types.Operator):
    """Export Godot materials from Blender materials.
Creates a .tres file for each used material in the Godot materials folder,
assigning ext_resources for base color, metallic, roughness, and normal textures. make sure the project root is assigned for calculating the relative godot paths"""
    bl_idname = "object.export_materials"
    bl_label = "Export Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        materials_folder = scene.godot_asset_materials_path
        textures_folder = scene.godot_asset_textures_path  # Folder where textures are exported
        project_root = bpy.path.abspath(scene.godot_project_root)
        
        # Validate folders
        if not materials_folder or not os.path.isdir(materials_folder):
            self.report({'ERROR'}, "Materials folder not set or invalid. Please set asset folder path first.")
            return {'CANCELLED'}
        if not textures_folder or not os.path.isdir(textures_folder):
            self.report({'ERROR'}, "Textures folder not set or invalid. Please export textures first.")
            return {'CANCELLED'}
        if not project_root or not os.path.isdir(project_root):
            self.report({'ERROR'}, "Godot project root not set or invalid.")
            return {'CANCELLED'}

        # Loop over each material in the blend file
        for mat in bpy.data.materials:
            if not mat.users or not mat.use_nodes:
                continue

            # Initialize texture paths
            base_color = ""
            metallic = ""
            roughness = ""
            normal = ""

            # Iterate over nodes; match using the image’s filename (in lowercase)
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    # Use the image’s filename for matching (lowercase)
                    filename = os.path.basename(bpy.path.abspath(node.image.filepath))
                    name_lower = filename.lower()
                    # Build the expected exported texture path by joining with textures_folder
                    texture_export_path = os.path.join(textures_folder, filename)
                    # Compute the Godot relative path using the project root.
                    godot_path = compute_godot_relative_path(texture_export_path, project_root)
                    
                    if "base" in name_lower or "albedo" in name_lower:
                        base_color = godot_path
                    elif "metal" in name_lower:
                        metallic = godot_path
                    elif "rough" in name_lower:
                        roughness = godot_path
                    elif "normal" in name_lower:
                        normal = godot_path

            # Skip if no textures found 
            if not (base_color or metallic or roughness or normal):
                continue

            # Build ext_resource lines and assignments using simple numeric IDs.
            ext_resources = []
            assignments = []
            counter = 1
            if base_color:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{base_color}" id="{counter}"]')
                assignments.append(f'albedo_texture = ExtResource("{counter}")')
                counter += 1
            if metallic:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{metallic}" id="{counter}"]')
                assignments.append(f'metallic = 1.0')
                assignments.append(f'metallic_texture = ExtResource("{counter}")')
                counter += 1
            if roughness:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{roughness}" id="{counter}"]')
                assignments.append(f'roughness_texture = ExtResource("{counter}")')
                counter += 1
            if normal:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{normal}" id="{counter}"]')
                assignments.append(f'normal_enabled = true')
                assignments.append(f'normal_texture = ExtResource("{counter}")')
                counter += 1

            # Generate the material header and resource block.
            material_header = f'[gd_resource type="StandardMaterial3D" load_steps=5 format=3 uid="uid://{mat.name.lower()}"]'
            resource_block = "[resource]\n"
            resource_block += f'resource_name = "{mat.name}"\n'
            resource_block += "cull_mode = 2\n"

            # Combine all parts.
            content = "\n".join([material_header] + ext_resources + [resource_block] + assignments)

            # Save the .tres file in the materials folder using the material name.
            tres_path = os.path.join(materials_folder, f"{mat.name}.tres")
            try:
                with open(tres_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                self.report({'WARNING'}, f"Could not export material {mat.name}: {e}")

        self.report({'INFO'}, "Exported materials.")
        return {'FINISHED'}

###############################
# Operator: Clear property
###############################

def clear_properties():
    del bpy.types.Scene.godot_suffix_tools_collapsible
    del bpy.types.Scene.godot_suffix
    del bpy.types.Scene.godot_collision_tools_collapsible
    del bpy.types.Scene.godot_collision_shape
    del bpy.types.Scene.godot_asset_data_collapsible
    del bpy.types.Scene.godot_texture_rescale
    del bpy.types.Scene.godot_texture_resolution
    del bpy.types.Scene.godot_asset_asset_path
    del bpy.types.Scene.godot_asset_scene_path
    del bpy.types.Scene.godot_asset_textures_path
    del bpy.types.Scene.godot_asset_materials_path
    del bpy.types.Material.godot_material_properties
    del bpy.types.Material.godot_material_properties_index
    del bpy.types.Object.godot_object_properties
    del bpy.types.Object.godot_object_properties_index
    del bpy.types.Mesh.godot_mesh_properties
    del bpy.types.Mesh.godot_mesh_properties_index

###############################
# init menu properties
###############################

def init_custom_asset_data_properties():
    bpy.types.Scene.godot_custom_material_properties_collapsible = BoolProperty(
        name="Custom Material Properties",
        default=True,
        description="Show custom material properties"
    )
    bpy.types.Scene.godot_custom_object_properties_collapsible = BoolProperty(
        name="Custom Object Properties",
        default=True,
        description="Show custom object properties"
    )
    bpy.types.Scene.godot_custom_mesh_properties_collapsible = BoolProperty(
        name="Custom Mesh Properties",
        default=True,
        description="Show custom mesh properties"
    )
    bpy.types.Scene.godot_custom_asset_data_collapsible = BoolProperty(
        name="Custom Asset Data",
        default=True,
        description="Show custom asset data (material, object, and mesh properties)"
    )
    bpy.types.Scene.godot_fix_root_bone_collapsible = BoolProperty(
        name="Fix Root Bone Rotations",
        default=True,
        description="Show fix root bone rotations options"
    )



###############################
# UI: Menu
###############################

class VIEW3D_PT_godot_tools_panel(bpy.types.Panel):
    """Panel for Godot Tools"""
    bl_label = "BlenGo"
    bl_idname = "VIEW3D_PT_godot_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenGo'
    
    def draw(self, context):
        layout = self.layout

        # --- Animation Tools Section ---
        anim_box = layout.box()
        row_anim = anim_box.row(align=True)
        anim_icon = "TRIA_DOWN" if context.scene.godot_fix_root_bone_collapsible else "TRIA_RIGHT"
        row_anim.prop(context.scene, "godot_fix_root_bone_collapsible", text="Animation tools", icon=anim_icon, emboss=True)
        if context.scene.godot_fix_root_bone_collapsible:
            # You can add more animation operators here if needed
            anim_box.operator("object.godot_tools", text="Run Root Fix")

        # --- Suffix Tools Section ---
        suffix_box = layout.box()
        row_suffix = suffix_box.row(align=True)
        suffix_icon = "TRIA_DOWN" if context.scene.godot_suffix_tools_collapsible else "TRIA_RIGHT"
        row_suffix.prop(context.scene, "godot_suffix_tools_collapsible", text="Suffix Tools", icon=suffix_icon, emboss=True)
        if context.scene.godot_suffix_tools_collapsible:
            suffix_box.prop(context.scene, "godot_suffix", text="Select Suffix")
            suffix_box.label(text=get_suffix_description(context.scene.godot_suffix))
            row_suffix_buttons = suffix_box.row(align=True)
            row_suffix_buttons.operator("object.suffix_tools_add", text="Add Suffix")
            row_suffix_buttons.operator("object.suffix_tools_remove", text="Remove Suffix")

        # --- Asset Folder Path Section ---
        asset_box = layout.box()
        row_asset = asset_box.row(align=True)
        asset_icon = "TRIA_DOWN" if context.scene.godot_asset_data_collapsible else "TRIA_RIGHT"
        row_asset.prop(context.scene, "godot_asset_data_collapsible", text="Asset Folder Path", icon=asset_icon, emboss=True)
        if context.scene.godot_asset_data_collapsible:
            asset_box.label(text="Set the project root before exporting materials")
            asset_box.prop(context.scene, "godot_project_root", text="Godot Project Root")
            #asset_box.label(text="Project path: " + context.scene.godot_project_root)
            asset_box.operator("object.set_asset_folder_path", text="Set Asset Folder")
            if context.scene.godot_asset_asset_path:
                
                asset_box.prop(context.scene, "godot_texture_rescale", text="Rescale Textures")
                if context.scene.godot_texture_rescale:
                    asset_box.prop(context.scene, "godot_texture_resolution", text="Texture Resolution")
                # Place export buttons in one row:
                export_row = asset_box.row(align=True)
                export_row.operator("object.export_gltf_fixed", text="Export Scene")
                export_row.operator("object.export_textures", text="Export Textures")
                export_row.operator("object.export_materials", text="Export Materials")
                asset_box.label(text="Scene Folder: " + context.scene.godot_asset_scene_path)


        # --- Custom Asset Data Section ---
        if context.active_object:
            asset_data_box = layout.box()
            # Top-level 
            
            row_data = asset_data_box.row(align=True)
            icon_data = "TRIA_DOWN" if context.scene.godot_custom_asset_data_collapsible else "TRIA_RIGHT"
            row_data.prop(context.scene, "godot_custom_asset_data_collapsible", text="Custom Asset Data", icon=icon_data, emboss=True)
            if context.scene.godot_custom_asset_data_collapsible:
                # Custom Material Properties
                
                if context.active_object.select_get():
                    obj = context.active_object
                    if obj.material_slots and obj.active_material:
                        mat = obj.material_slots[obj.active_material_index].material
                        row_mat = asset_data_box.row(align=True)
                        icon_mat = "TRIA_DOWN" if context.scene.godot_custom_material_properties_collapsible else "TRIA_RIGHT"
                        row_mat.prop(context.scene, "godot_custom_material_properties_collapsible", text="Custom Material Properties", icon=icon_mat, emboss=False)
                        if context.scene.godot_custom_material_properties_collapsible:
                            sub_box = asset_data_box.box()
                            for i, item in enumerate(mat.godot_material_properties):
                                sub_sub_box = sub_box.box()
                                row = sub_sub_box.row()
                                row.label(text=item.prop_name)
                                row.prop(item, "prop_description", text="Godot path")
                                op = row.operator("object.delete_material_property", text="", icon="PANEL_CLOSE")
                                op.index = i
                            sub_box.operator("object.add_material_property", text="Add Material Property")
                # Custom Object Properties
                
                row_obj = asset_data_box.row(align=True)
                icon_obj = "TRIA_DOWN" if context.scene.godot_custom_object_properties_collapsible else "TRIA_RIGHT"
                row_obj.prop(context.scene, "godot_custom_object_properties_collapsible", text="Custom Object Properties", icon=icon_obj, emboss=False)
                if context.scene.godot_custom_object_properties_collapsible:
                    sub_box2 = asset_data_box.box()
                    for i, item in enumerate(context.active_object.godot_object_properties):
                        sub_sub_box = sub_box2.box()
                        row = sub_sub_box.row(align=True)
                        row.label(text=item.prop_name)
                        row.prop(item, "prop_selection", text="Option")
                        if item.prop_selection == "Custom":
                            row.prop(item, "prop_raw", text="tag")
                        elif item.prop_selection == "Script":
                            row.prop(item, "prop_raw", text="Script path")
                        row.operator("object.delete_object_property", text="", icon="PANEL_CLOSE").index = i
                    sub_box2.operator("object.add_object_property", text="Add Object Property")
                # Custom Mesh Properties (if the active object is mesh)
                
                if context.active_object.type == 'MESH':
                    row_mesh = asset_data_box.row(align=True)
                    icon_mesh = "TRIA_DOWN" if context.scene.godot_custom_mesh_properties_collapsible else "TRIA_RIGHT"
                    row_mesh.prop(context.scene, "godot_custom_mesh_properties_collapsible", text="Custom Mesh Properties", icon=icon_mesh, emboss=False)
                    if context.scene.godot_custom_mesh_properties_collapsible:
                        mesh = context.active_object.data
                        if hasattr(mesh, "godot_mesh_properties"):
                            sub_mesh_box = asset_data_box.box()
                            for i, item in enumerate(mesh.godot_mesh_properties):
                                sub_box_mesh = sub_mesh_box.box()
                                row = sub_box_mesh.row(align=True)
                                row.label(text=item.prop_name)
                                row.prop(item, "prop_selection", text="Option")
                                if item.prop_selection == "Custom":
                                    row.prop(item, "prop_description", text="tag:")
                                row.operator("object.delete_godot_mesh_property", text="", icon="PANEL_CLOSE").index = i
                            sub_mesh_box.operator("object.add_godot_mesh_property", text="Add Godot Mesh Property")

###############################
# Registration
###############################
classes = [
    VIEW3D_PT_godot_tools_panel,
    OBJECT_OT_godot_tools,
    OBJECT_OT_suffix_tools_add,
    OBJECT_OT_suffix_tools_remove,
    OBJECT_OT_add_collision,
    OBJECT_OT_add_material_property,
    OBJECT_OT_delete_material_property,
    OBJECT_OT_add_object_property,
    OBJECT_OT_delete_object_property,
    OBJECT_OT_set_asset_folder_path,
    OBJECT_OT_export_textures,
    OBJECT_OT_export_gltf_fixed,
    GodotMaterialProperty,
    GodotObjectProperty,
    GodotMeshProperty,
    OBJECT_OT_add_godot_mesh_property,
    OBJECT_OT_delete_godot_mesh_property,
    OBJECT_OT_export_materials,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    init_suffix_properties()
    init_custom_asset_data_properties()
    init_godot_root_project()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    clear_properties()

if __name__ == "__main__":
    register()
    
    