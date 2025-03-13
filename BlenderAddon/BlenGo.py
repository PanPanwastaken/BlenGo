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
    "version": (0, 4, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > BlenGo",
    "description": "A toolset for Blender/Godot pipelines",
    "category": "Import-Export",
}

###############################
# Imports & Utilities
###############################

import bpy
import os, re, shutil, random, string
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper
import json 

def set_custom_property(target, prop_name, value):
    """
    Sets a custom property on a target (object, material, mesh) and updates its RNA_UI.
    """
    target[prop_name] = value
    if "_RNA_UI" not in target:
        target["_RNA_UI"] = {}
    target["_RNA_UI"][prop_name] = {"description": value}

###############################
# Update Callback Functions
###############################
def gather_material_extras():
    """Collect a dictionary mapping material names to their custom property data."""
    extras = {}
    for mat in bpy.data.materials:
        # Use the new naming convention
        key = "blengo_material:" + mat.name
        if key in mat:
            extras[mat.name] = {key: mat[key]}
    return extras

def inject_extras_to_gltf(gltf_path, material_extras):
    """Open the glTF file at gltf_path, inject material extras, and save it back."""
    with open(gltf_path, "r", encoding="utf-8") as f:
        gltf_data = json.load(f)
    for mat in gltf_data.get("materials", []):
        name = mat.get("name")
        if name and name in material_extras:
            mat["extras"] = material_extras[name]
    with open(gltf_path, "w", encoding="utf-8") as f:
        json.dump(gltf_data, f, indent=2)

def update_obj_prop(self, context):
    obj = context.active_object
    if obj:
        if self.prop_selection in {"CastShadowOn", "CastShadowOff"}:
            final_val = self.prop_selection
        elif self.prop_selection == "Script":
            final_val = "scriptpath:" + self.prop_raw
        else:
            final_val = self.prop_raw
        set_custom_property(obj, self.prop_name, final_val)

def update_mesh_prop_selection(self, context):
    if self.prop_selection != "Custom":
        self.prop_description = self.prop_selection

def update_material_custom_property(self, context):
    obj = context.object
    if obj and obj.active_material and self.prop_name:
        if hasattr(self, "prop_option") and self.prop_option == "ExtGodotMtrl":
            self.prop_description = "ExtGodotMtrl"
        mat = obj.active_material
        set_custom_property(mat, self.prop_name, self.prop_description)
        # --- update scene metadata ---
        scene = context.scene
        try:
            metadata = json.loads(scene.get("godot_material_metadata", "{}"))
        except Exception:
            metadata = {}
        metadata[mat.name] = {self.prop_name: self.prop_description}
        scene["godot_material_metadata"] = json.dumps(metadata)

def update_obj_prop_desc(self, context):
    obj = context.active_object
    if obj:
        set_custom_property(obj, self.prop_name, self.prop_description)

def update_godot_mesh_prop_desc(self, context):
    obj = context.active_object
    if obj and obj.data and hasattr(obj.data, "godot_mesh_properties"):
        mesh = obj.data
        set_custom_property(mesh, self.prop_name, self.prop_description)

###############################
# Property Groups
###############################

class GodotMaterialProperty(bpy.types.PropertyGroup):
    prop_name: StringProperty(
        name="Property Name",
        description="Automatically set from the active material",
        default=""
    )
    prop_option: EnumProperty(
        name="Material Option",
        description="Choose a custom Godot path or use generated material",
        items=[
            ("Custom", "Custom", "Enter custom Godot path"),
            ("ExtGodotMtrl", "Generated", "Use generated Godot material")
        ],
        default="Custom",
        update=update_material_custom_property
    )
    prop_description: StringProperty(
        name="Godot path:",
        default="",
        description="Custom Godot path (or 'ExtGodotMtrl' for generated)",
        update=update_material_custom_property
    )

class GodotObjectProperty(bpy.types.PropertyGroup):
    prop_name: StringProperty(
        name="Property Name",
        description="Automatically set from the active object"
    )
    prop_selection: EnumProperty(
        name="Option",
        description="Select a predefined option, Script, or Custom",
        items=[
            ("CastShadowOn", "CastShadowOn", "Enable cast shadow"),
            ("CastShadowOff", "CastShadowOff", "Disable cast shadow"),
            ("Script", "Script", "Assign a script path"),
            ("Custom", "Custom", "Enter custom value")
        ],
        default="Custom",
        update=update_obj_prop
    )
    prop_raw: StringProperty(
        name="Godot path:",
        default="",
        description="User entered text",
        update=update_obj_prop
    )

    def get_prop_description(self):
        return "scriptpath:" + self.prop_raw if self.prop_selection == "Script" else self.prop_raw

    def set_prop_description(self, value):
        if self.prop_selection == "Script":
            prefix = "scriptpath:"
            self.prop_raw = value[len(prefix):] if value.startswith(prefix) else value
        else:
            self.prop_raw = value

    prop_description: StringProperty(
        name="Godot path:",
        get=get_prop_description,
        set=set_prop_description,
        description="Custom Godot path for this object property"
    )

class GodotMeshProperty(bpy.types.PropertyGroup):
    prop_name: StringProperty(
        name="Property Name",
        description="Automatically set from the active mesh"
    )
    prop_selection: EnumProperty(
        name="Option",
        description="Select a predefined option or Custom",
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
    prop_description: StringProperty(
        name="Godot path:",
        default="",
        description="Custom Godot path for this mesh property",
        update=update_godot_mesh_prop_desc
    )

###############################
# Operators
###############################

# --- Animation Tools ---
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
    root_bone = edit_bones.new(root_bone_name)
    root_bone.head = hips_bone.head.copy()
    root_bone.tail = hips_bone.tail.copy()
    root_bone.roll = hips_bone.roll

    hips_bone.parent = root_bone
    bpy.ops.object.mode_set(mode='OBJECT')

    action = armature.animation_data.action if armature.animation_data else None
    if not action:
        print(f"No animation found in {armature.name}")
        return

    new_action = action.copy()
    new_action.name = f"{action.name}_root"
    armature.animation_data.action = new_action
    existing_paths = set()

    for fcurve in list(action.fcurves):
        key = f'pose.bones["{hip_bone_name}"].location'
        if fcurve.data_path.startswith(key):
            new_data_path = fcurve.data_path.replace(hip_bone_name, root_bone_name)
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
    """Fix root bone rotations by duplicating the hip bone"""
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

# --- Suffix Tools ---
class OBJECT_OT_suffix_tools_add(bpy.types.Operator):
    """Add the selected suffix to the object's name"""
    bl_idname = "object.suffix_tools_add"
    bl_label = "Add Suffix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        suffix = context.scene.godot_suffix
        for obj in context.selected_objects:
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
        for obj in context.selected_objects:
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
        "-convcolonly": "Suffix '-convcolonly' is for convex collision-only objects."
    }
    return descriptions.get(suffix, "No description available for this suffix.")

# --- Collision Tools ---
class OBJECT_OT_add_collision(bpy.types.Operator):
    """Add a collision object to each selected object."""
    bl_idname = "object.add_collision"
    bl_label = "Add Collision Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        collision_shape = context.scene.godot_collision_shape
        for obj in context.selected_objects:
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

# --- Asset Folder & Texture Export ---
class OBJECT_OT_set_asset_folder_path(bpy.types.Operator, ImportHelper):
    """Set the asset folder path for the Godot project."""
    bl_idname = "object.set_asset_folder_path"
    bl_label = "Set Assets Folder"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ""
    use_filter_folder = True
    filter_glob: StringProperty(default="", options={'HIDDEN'})
    
    def draw(self, context):
        pass

    def invoke(self, context, event):
        scene = context.scene
        self.filemode = 2  # Directory mode
        if scene.godot_asset_asset_path:
            self.asset_folder = os.path.dirname(scene.godot_asset_asset_path)
        elif bpy.data.filepath:
            self.asset_folder = os.path.dirname(bpy.data.filepath)
        else:
            self.asset_folder = os.path.expanduser("~")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        project_folder = os.path.dirname(self.filepath)
        if not os.path.isdir(project_folder):
            self.report({'ERROR'}, f"Invalid folder path: {project_folder}")
            return {'CANCELLED'}
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Please save the blend file first.")
            return {'CANCELLED'}
        blend_name = os.path.splitext(os.path.basename(blend_file))[0]
        asset_path = os.path.abspath(os.path.join(project_folder, blend_name))
        if os.path.exists(asset_path):
            try:
                shutil.rmtree(asset_path)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to remove existing asset folder: {e}")
                return {'CANCELLED'}
        os.makedirs(asset_path)
        scene_folder = os.path.join(asset_path, "scene")
        textures_folder = os.path.join(asset_path, "textures")
        materials_folder = os.path.join(asset_path, "materials")
        for folder in [scene_folder, textures_folder, materials_folder]:
            os.makedirs(folder, exist_ok=True)
        scene = context.scene
        scene.godot_asset_asset_path = asset_path
        scene.godot_asset_scene_path = scene_folder
        scene.godot_asset_textures_path = textures_folder
        scene.godot_asset_materials_path = materials_folder
        self.report({'INFO'}, "Asset folders created and saved")
        return {'FINISHED'}

class OBJECT_OT_export_textures(bpy.types.Operator):
    """Export all textures used in the blend file to the textures folder."""
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
                filename = os.path.basename(img.filepath) if img.filepath else img.name + ".png"
                out_filepath = os.path.join(textures_folder, filename)
                try:
                    if rescale and resolution:
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

# --- GLTF Export ---
class OBJECT_OT_export_gltf_fixed(bpy.types.Operator):
    """Export the scene to glTF using a preset scene folder and inject custom material extras."""
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
        result = bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath=self.filepath)
        return result

    def execute(self, context):
        extras = gather_material_extras()
        inject_extras_to_gltf(self.filepath, extras)
        self.report({'INFO'}, "Exported glTF and injected material extras metadata.")
        return {'FINISHED'}

# --- Custom Material, Object, and Mesh Properties ---
class OBJECT_OT_add_material_property(bpy.types.Operator):
    """Add a custom material property to the active material."""
    bl_idname = "object.add_material_property"
    bl_label = "Add Material Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.material_slots or obj.active_material is None:
            self.report({'WARNING'}, "Active object or material not found.")
            return {'CANCELLED'}
        mat = obj.material_slots[obj.active_material_index].material
        prop_name = "blengo_material:" + mat.name
        set_custom_property(mat, prop_name, "")
        new_item = mat.godot_material_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        self.report({'INFO'}, f"Added custom material property '{prop_name}'.")
        return {'FINISHED'}

class OBJECT_OT_delete_material_property(bpy.types.Operator):
    """Delete a custom material property from the active material."""
    bl_idname = "object.delete_material_property"
    bl_label = "Delete Material Property"
    bl_options = {'REGISTER', 'UNDO'}
    index: IntProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.material_slots or obj.active_material is None:
            self.report({'WARNING'}, "No active material found.")
            return {'CANCELLED'}
        mat = obj.material_slots[obj.active_material_index].material
        try:
            mat.godot_material_properties.remove(self.index)
            prop = "blengo_material:" + mat.name
            if prop in mat: 
                del mat[prop]
            if "_RNA_UI" in mat and prop in mat["_RNA_UI"]:
                del mat["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted material property.")
        return {'FINISHED'}

class OBJECT_OT_add_object_property(bpy.types.Operator):
    """Add a custom object property to the active object."""
    bl_idname = "object.add_object_property"
    bl_label = "Add Object Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        prop_name = "blengo_object:" + obj.name
        set_custom_property(obj, prop_name, "")
        new_item = obj.godot_object_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        new_item.prop_selection = "Custom"
        self.report({'INFO'}, f"Added custom object property '{prop_name}'.")
        return {'FINISHED'}

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
            prop = "blengo_object:" + obj.name
            if prop in obj: 
                del obj[prop]
            if "_RNA_UI" in obj and prop in obj["_RNA_UI"]:
                del obj["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted object property.")
        return {'FINISHED'}

class OBJECT_OT_add_godot_mesh_property(bpy.types.Operator):
    """Add a custom mesh property to the active mesh."""
    bl_idname = "object.add_godot_mesh_property"
    bl_label = "Add Godot Mesh Property"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh found.")
            return {'CANCELLED'}
        mesh = obj.data
        prop_name = "blengo_mesh:" + mesh.name
        set_custom_property(mesh, prop_name, "")
        new_item = mesh.godot_mesh_properties.add()
        new_item.prop_name = prop_name
        new_item.prop_description = ""
        new_item.prop_selection = "Custom"
        self.report({'INFO'}, f"Added custom Godot mesh property '{prop_name}'.")
        return {'FINISHED'}

class OBJECT_OT_delete_godot_mesh_property(bpy.types.Operator):
    """Delete a custom Godot mesh property from the active mesh."""
    bl_idname = "object.delete_godot_mesh_property"
    bl_label = "Delete Godot Mesh Property"
    bl_options = {'REGISTER', 'UNDO'}
    index: IntProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.data or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh found.")
            return {'CANCELLED'}
        mesh = obj.data
        try:
            mesh.godot_mesh_properties.remove(self.index)
            prop = "blengo_mesh:" + mesh.name
            if prop in mesh: 
                del mesh[prop]
            if "_RNA_UI" in mesh and prop in mesh["_RNA_UI"]:
                del mesh["_RNA_UI"][prop]
        except Exception as e:
            self.report({'WARNING'}, f"Could not delete property: {str(e)}")
            return {'CANCELLED'}
        self.report({'INFO'}, "Deleted Godot mesh property.")
        return {'FINISHED'}

# --- Material Export Operator ---
def compute_godot_relative_path(target_path, project_root):
    target_path = os.path.abspath(target_path)
    project_root = os.path.abspath(project_root)
    rel_path = os.path.relpath(target_path, project_root)
    return "res://" + rel_path.replace("\\", "/")

class OBJECT_OT_export_materials(bpy.types.Operator):
    """Export Godot materials from selected objects and update custom property to 'ExtGodotMtrl'."""
    bl_idname = "object.export_materials"
    bl_label = "Export Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        materials_folder = scene.godot_asset_materials_path
        textures_folder = scene.godot_asset_textures_path
        project_root = bpy.path.abspath(scene.godot_project_root)
        
        if not (materials_folder and os.path.isdir(materials_folder)):
            self.report({'ERROR'}, "Materials folder not set or invalid.")
            return {'CANCELLED'}
        if not (textures_folder and os.path.isdir(textures_folder)):
            self.report({'ERROR'}, "Textures folder not set or invalid. Please export textures first.")
            return {'CANCELLED'}
        if not (project_root and os.path.isdir(project_root)):
            self.report({'ERROR'}, "Godot project root not set or invalid.")
            return {'CANCELLED'}
        
        selected_materials = {slot.material for obj in context.selected_objects 
                              if obj.type == 'MESH' and obj.material_slots 
                              for slot in obj.material_slots if slot.material}
        
        for mat in selected_materials:
            if not mat.users or not mat.use_nodes:
                continue
            
            base_color = metallic = roughness = normal = ""
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    filename = os.path.basename(bpy.path.abspath(node.image.filepath))
                    name_lower = filename.lower()
                    texture_export_path = os.path.join(textures_folder, filename)
                    godot_path = compute_godot_relative_path(texture_export_path, project_root)
                    if "base" in name_lower or "albedo" in name_lower:
                        base_color = godot_path
                    elif "metal" in name_lower:
                        metallic = godot_path
                    elif "rough" in name_lower:
                        roughness = godot_path
                    elif "normal" in name_lower:
                        normal = godot_path
            if not (base_color or metallic or roughness or normal):
                continue
            
            ext_resources, assignments = [], []
            counter = 1
            if base_color:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{base_color}" id="{counter}"]')
                assignments.append(f'albedo_texture = ExtResource("{counter}")')
                counter += 1
            if metallic:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{metallic}" id="{counter}"]')
                assignments.extend([f'metallic = 1.0', f'metallic_texture = ExtResource("{counter}")'])
                counter += 1
            if roughness:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{roughness}" id="{counter}"]')
                assignments.append(f'roughness_texture = ExtResource("{counter}")')
                counter += 1
            if normal:
                ext_resources.append(f'[ext_resource type="Texture2D" path="{normal}" id="{counter}"]')
                assignments.extend([f'normal_enabled = true', f'normal_texture = ExtResource("{counter}")'])
                counter += 1

            material_header = f'[gd_resource type="StandardMaterial3D" load_steps=5 format=3 uid="uid://{mat.name.lower()}"]'
            resource_block = "[resource]\n" + f'resource_name = "{mat.name}"\n' + "cull_mode = 2\n"
            content = "\n".join([material_header] + ext_resources + [resource_block] + assignments)
            tres_path = os.path.join(materials_folder, f"{mat.name}.tres")
            try:
                with open(tres_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                self.report({'WARNING'}, f"Could not export material {mat.name}: {e}")
                continue

            # Update the material's custom property using the naming convention.
            prop_name = "blengo_material:" + mat.name
            set_custom_property(mat, prop_name, "ExtGodotMtrl")
            if mat.godot_material_properties:
                mat.godot_material_properties[0].prop_option = "ExtGodotMtrl"
                mat.godot_material_properties[0].prop_description = "ExtGodotMtrl"
            else:
                custom_prop = mat.godot_material_properties.add()
                custom_prop.prop_option = "ExtGodotMtrl"
                custom_prop.prop_description = "ExtGodotMtrl"
            
            # Update scene metadata in the same way as in the custom property update.
            try:
                metadata = json.loads(scene.get("godot_material_metadata", "{}"))
            except Exception:
                metadata = {}
            metadata[mat.name] = {prop_name: "ExtGodotMtrl"}
            scene["godot_material_metadata"] = json.dumps(metadata)
        
        self.report({'INFO'}, "Exported materials and updated custom properties and scene metadata to 'ExtGodotMtrl'.")
        return {'FINISHED'}

###############################
# Initialization Functions
###############################

def init_properties():
    bpy.types.Scene.godot_suffix_tools_collapsible = BoolProperty(
        name="Suffix Tools", default=True,
        description="Add suffixes recognized by Godot engine for various actions")
    bpy.types.Scene.godot_suffix = EnumProperty(
        name="Suffix",
        description="Select the suffix to work with",
        items=[
            ("-navmesh", "-navmesh", "Suffix for navigation meshes"),
            ("-occ", "-occ", "Suffix for occlusion objects"),
            ("-rigid", "-rigid", "Suffix for rigid bodies"),
            ("-cycle", "-cycle", "Suffix for cyclic animations or cycles"),
            ("-vehicle", "-vehicle", "Suffix for vehicles"),
            ("-wheel", "-wheel", "Suffix for wheels"),
            ("-col", "-col", "Suffix for collision objects"),
            ("-convcol", "-convcol", "Suffix for convex collisions"),
            ("-colonly", "-colonly", "Suffix for collision-only objects"),
            ("-convcolonly", "-convcolonly", "Suffix for convex collision-only objects")
        ],
        default="-rigid"
    )
    bpy.types.Scene.godot_collision_tools_collapsible = BoolProperty(
        name="Add Collision for Selected Objects", default=True,
        description="Show collision tools for adding a collision object to selected objects")
    bpy.types.Scene.godot_collision_shape = EnumProperty(
        name="Shape:",
        description="Choose the shape of the collision object",
        items=[("CUBE", "Cube", "Cube"), ("CYLINDER", "Cylinder", "Cylinder (5 vertices)")],
        default="CUBE"
    )
    bpy.types.Scene.godot_asset_data_collapsible = BoolProperty(
        name="Asset Folder Path", default=True,
        description="Set asset folder path and create asset subfolders for the blend file")
    bpy.types.Scene.godot_texture_rescale = BoolProperty(
        name="Rescale Textures", default=False,
        description="Export textures scaled to the chosen resolution")
    bpy.types.Scene.godot_texture_resolution = EnumProperty(
        name="Texture Resolution",
        items=[("1024", "1K", "Export textures at 1K resolution"),
               ("2048", "2K", "Export textures at 2K resolution"),
               ("4096", "4K", "Export textures at 4K resolution")],
        default="1024"
    )
    bpy.types.Scene.godot_asset_asset_path = StringProperty(
        name="Asset Folder", description="Asset folder for this blend file", default=""
    )
    bpy.types.Scene.godot_asset_scene_path = StringProperty(
        name="Scene Folder", description="Scene subfolder path", default=""
    )
    bpy.types.Scene.godot_asset_textures_path = StringProperty(
        name="Textures Folder", description="Textures subfolder path", default=""
    )
    bpy.types.Scene.godot_asset_materials_path = StringProperty(
        name="Materials Folder", description="Materials subfolder path", default=""
    )
    bpy.types.Scene.godot_project_root = StringProperty(
        name="Godot Project Root",
        description="The root folder of your Godot project (corresponds to res://)",
        default="",
        subtype='DIR_PATH'
    )
    bpy.types.Material.godot_material_properties = CollectionProperty(type=GodotMaterialProperty)
    bpy.types.Material.godot_material_properties_index = IntProperty(name="Index", default=0)
    bpy.types.Object.godot_object_properties = CollectionProperty(type=GodotObjectProperty)
    bpy.types.Object.godot_object_properties_index = IntProperty(name="Index", default=0)
    bpy.types.Mesh.godot_mesh_properties = CollectionProperty(type=GodotMeshProperty)
    bpy.types.Mesh.godot_mesh_properties_index = IntProperty(name="Index", default=0)
    bpy.types.Scene.godot_custom_material_properties_collapsible = BoolProperty(
        name="Custom Material Properties", default=True,
        description="Show custom material properties")
    bpy.types.Scene.godot_custom_object_properties_collapsible = BoolProperty(
        name="Custom Object Properties", default=True,
        description="Show custom object properties")
    bpy.types.Scene.godot_custom_mesh_properties_collapsible = BoolProperty(
        name="Custom Mesh Properties", default=True,
        description="Show custom mesh properties")
    bpy.types.Scene.godot_custom_asset_data_collapsible = BoolProperty(
        name="Custom Asset Data", default=True,
        description="Show custom asset data (material, object, and mesh properties)")
    bpy.types.Scene.godot_fix_root_bone_collapsible = BoolProperty(
        name="Fix Root Bone Rotations", default=True,
        description="Show fix root bone rotations options")

###############################
# UI Panel
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
        scene = context.scene
        
        anim_box = layout.box()
        row_anim = anim_box.row(align=True)
        anim_icon = "TRIA_DOWN" if scene.godot_fix_root_bone_collapsible else "TRIA_RIGHT"
        row_anim.prop(scene, "godot_fix_root_bone_collapsible", text="Animation tools", icon=anim_icon)
        if scene.godot_fix_root_bone_collapsible:
            anim_box.operator("object.godot_tools", text="Run Root Fix")
        
        suffix_box = layout.box()
        row_suffix = suffix_box.row(align=True)
        suffix_icon = "TRIA_DOWN" if scene.godot_suffix_tools_collapsible else "TRIA_RIGHT"
        row_suffix.prop(scene, "godot_suffix_tools_collapsible", text="Suffix Tools", icon=suffix_icon)
        if scene.godot_suffix_tools_collapsible:
            suffix_box.prop(scene, "godot_suffix", text="Select Suffix")
            suffix_box.label(text=get_suffix_description(scene.godot_suffix))
            row_suffix_buttons = suffix_box.row(align=True)
            row_suffix_buttons.operator("object.suffix_tools_add", text="Add Suffix")
            row_suffix_buttons.operator("object.suffix_tools_remove", text="Remove Suffix")
        
        asset_box = layout.box()
        row_asset = asset_box.row(align=True)
        asset_icon = "TRIA_DOWN" if scene.godot_asset_data_collapsible else "TRIA_RIGHT"
        row_asset.prop(scene, "godot_asset_data_collapsible", text="Asset Folder Path", icon=asset_icon)
        if scene.godot_asset_data_collapsible:
            asset_box.label(text="Set the project root before exporting materials")
            asset_box.prop(scene, "godot_project_root", text="Godot Project Root")
            asset_box.operator("object.set_asset_folder_path", text="Set Asset Folder")
            if scene.godot_asset_asset_path:
                asset_box.prop(scene, "godot_texture_rescale", text="Rescale Textures")
                if scene.godot_texture_rescale:
                    asset_box.prop(scene, "godot_texture_resolution", text="Texture Resolution")
                export_row = asset_box.row(align=True)
                export_row.operator("object.export_gltf_fixed", text="Export Scene")
                export_row.operator("object.export_textures", text="Export Textures")
                export_row.operator("object.export_materials", text="Export Materials")
                asset_box.label(text="Scene Folder: " + scene.godot_asset_scene_path)
        
        if context.active_object:
            asset_data_box = layout.box()
            row_data = asset_data_box.row(align=True)
            icon_data = "TRIA_DOWN" if scene.godot_custom_asset_data_collapsible else "TRIA_RIGHT"
            row_data.prop(scene, "godot_custom_asset_data_collapsible", text="Custom Asset Data", icon=icon_data)
            if scene.godot_custom_asset_data_collapsible:
                obj = context.active_object
                if obj.material_slots and obj.active_material:
                    mat = obj.material_slots[obj.active_material_index].material
                    row_mat = asset_data_box.row(align=True)
                    icon_mat = "TRIA_DOWN" if scene.godot_custom_material_properties_collapsible else "TRIA_RIGHT"
                    row_mat.prop(scene, "godot_custom_material_properties_collapsible", text="Custom Material Properties", icon=icon_mat)
                    if scene.godot_custom_material_properties_collapsible:
                        sub_box = asset_data_box.box()
                        for i, item in enumerate(mat.godot_material_properties):
                            sub_sub_box = sub_box.box()
                            row = sub_sub_box.row()
                            row.label(text=item.prop_name)
                            row.prop(item, "prop_description", text="Godot path")
                            op = row.operator("object.delete_material_property", text="", icon="PANEL_CLOSE")
                            op.index = i
                        sub_box.operator("object.add_material_property", text="Add Material Property")
                row_obj = asset_data_box.row(align=True)
                icon_obj = "TRIA_DOWN" if scene.godot_custom_object_properties_collapsible else "TRIA_RIGHT"
                row_obj.prop(scene, "godot_custom_object_properties_collapsible", text="Custom Object Properties", icon=icon_obj)
                if scene.godot_custom_object_properties_collapsible:
                    sub_box2 = asset_data_box.box()
                    for i, item in enumerate(obj.godot_object_properties):
                        sub_sub_box = sub_box2.box()
                        row = sub_sub_box.row(align=True)
                        row.label(text=item.prop_name)
                        row.prop(item, "prop_selection", text="Option")
                        if item.prop_selection in {"Custom", "Script"}:
                            row.prop(item, "prop_raw", text="tag")
                        row.operator("object.delete_object_property", text="", icon="PANEL_CLOSE").index = i
                    sub_box2.operator("object.add_object_property", text="Add Object Property")
                if obj.type == 'MESH':
                    row_mesh = asset_data_box.row(align=True)
                    icon_mesh = "TRIA_DOWN" if scene.godot_custom_mesh_properties_collapsible else "TRIA_RIGHT"
                    row_mesh.prop(scene, "godot_custom_mesh_properties_collapsible", text="Custom Mesh Properties", icon=icon_mesh)
                    if scene.godot_custom_mesh_properties_collapsible:
                        mesh = obj.data
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
    OBJECT_OT_set_asset_folder_path,
    OBJECT_OT_export_textures,
    OBJECT_OT_export_gltf_fixed,
    OBJECT_OT_export_materials,
    OBJECT_OT_add_material_property,
    OBJECT_OT_delete_material_property,
    OBJECT_OT_add_object_property,
    OBJECT_OT_delete_object_property,
    OBJECT_OT_add_godot_mesh_property,
    OBJECT_OT_delete_godot_mesh_property,
    GodotMaterialProperty,
    GodotObjectProperty,
    GodotMeshProperty,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    init_properties()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    props = [
        "godot_suffix_tools_collapsible", "godot_suffix", "godot_collision_tools_collapsible",
        "godot_collision_shape", "godot_asset_data_collapsible", "godot_texture_rescale",
        "godot_texture_resolution", "godot_asset_asset_path", "godot_asset_scene_path",
        "godot_asset_textures_path", "godot_asset_materials_path", "godot_project_root",
        "godot_custom_material_properties_collapsible", "godot_custom_object_properties_collapsible",
        "godot_custom_mesh_properties_collapsible", "godot_custom_asset_data_collapsible",
        "godot_fix_root_bone_collapsible"
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
    for typ in [bpy.types.Material, bpy.types.Object, bpy.types.Mesh]:
        for attr in ["godot_material_properties", "godot_material_properties_index", 
                     "godot_object_properties", "godot_object_properties_index",
                     "godot_mesh_properties", "godot_mesh_properties_index"]:
            if hasattr(typ, attr):
                delattr(typ, attr)

if __name__ == "__main__":
    register()
