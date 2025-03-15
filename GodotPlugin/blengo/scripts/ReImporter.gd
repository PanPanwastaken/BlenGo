@tool
extends Node

var file_path: String
var material_changes := {}

func set_file_path(path: String) -> void:
	file_path = path
	print("ReImporter: File path set to ", file_path)

# Called for each material item.
func process_material_item(data: String) -> void:
	print("Processing Material item: ", data)
	print("From file: ", file_path)
	# Expected format:
	# "Type: Material, Name: Example_material, Property: {\"raw\": \"ExtGodotMtrl\"}"
	var parts = data.split(",", false)
	if parts.size() < 3:
		print("Invalid data format for material: ", data)
		return

	var material_name = parts[1].replace("Name:", "").strip_edges()
	var property_str = parts[2].replace("Property:", "").strip_edges()
	
	var material_settings = {}
	if property_str.begins_with("{") and property_str.ends_with("}"):
		var json_parser = JSON.new()
		var err = json_parser.parse(property_str)
		if err != OK:
			print("Error parsing JSON for material property: ", property_str)
			material_settings = {}
		else:
			material_settings = json_parser.get_data()
	else:
		# Wrap non-JSON values in a dictionary under "raw"
		material_settings = {"raw": property_str}
	
	material_changes[material_name] = material_settings
	rewrite_import_file()

func process_mesh_item(data: String) -> void:
	print("Processing Mesh item: ", data)
	print("From file: ", file_path)
	# Your mesh processing code here.

func process_object_item(data: String) -> void:
	print("Processing Object item: ", data)
	print("From file: ", file_path)
	# Your object processing code here.

# This function reads, updates (or appends), and rewrites the .import file
func rewrite_import_file() -> void:
	if file_path == "":
		print("File path not set.")
		return
	# Determine the import file path (e.g., "asset.glb.import")
	var import_file_path = file_path + ".import"
	var file = FileAccess.open(import_file_path, FileAccess.READ)
	if file == null:
		print("Failed to open import file: ", import_file_path)
		return
	var content = file.get_as_text()
	file.close()
	
	# Generate the new _subresources block text from the material_changes dictionary
	var new_subresources = _generate_materials_block()
	if new_subresources == "":
		print("No material changes to apply.")
		return

	# Use a regex to see if an _subresources block already exists
	var regex = RegEx.new()
	var pattern = r"(?s)_subresources\s*=\s*\{.*?\}"
	var err = regex.compile(pattern)
	if err != OK:
		print("Regex compilation error.")
		return
	if regex.search(content):
		# Replace the existing _subresources block with the new one
		content = regex.sub(content, new_subresources)
	else:
		# Append the new _subresources block at the end.
		content += "\n" + new_subresources + "\n"
	# Write the modified content back to the .import file
	file = FileAccess.open(import_file_path, FileAccess.WRITE)
	if file:
		file.store_string(content)
		file.close()
		print("Rewritten import file: ", import_file_path)
	else:
		print("Failed to write to import file: ", import_file_path)

# create the _subresources block
func _generate_materials_block() -> String:
	if material_changes.size() == 0:
		return ""
	var block = "_subresources={\n"
	block += "\t\"materials\": {\n"
	for material_name in material_changes.keys():
		var settings = material_changes[material_name]
		var new_settings = {}
		if settings.has("raw"):
			var raw_value = str(settings["raw"])
			if raw_value == "ExtGodotMtrl":
				new_settings["use_external/enabled"] = true
				new_settings["use_external/path"] = _compute_material_path(material_name)
			elif raw_value.begins_with("res://"):
				new_settings["use_external/enabled"] = true
				new_settings["use_external/path"] = raw_value
			else:
				new_settings = settings
		else:
			new_settings = settings
		
		block += "\t\t\"" + material_name + "\": {\n"
		for key in new_settings.keys():
			var value = new_settings[key]
			var value_str = ""
			if typeof(value) == TYPE_BOOL:
				value_str = "true" if value else "false"
			else:
				value_str = "\"" + str(value) + "\""
			block += "\t\t\t\"" + key + "\": " + value_str + ",\n"
		# Remove trailing comma/newline for this material.
		block = block.rstrip(",\n") + "\n"
		block += "\t\t},\n"
	# Remove trailing comma/newline for the materials block.
	block = block.rstrip(",\n") + "\n"
	block += "\t}\n"
	block += "}"
	return block

# Computes the external material path based on the GLB file path and material name
func _compute_material_path(material_name: String) -> String:
	# Get the directory containing the GLB file.
	var base_dir = _get_base_dir(file_path)  # e.g., "res://assets/this_asset_folder/scene"
	# Get the parent directory (one level up).
	var parent_dir = _get_base_dir(base_dir)   # e.g., "res://assets/this_asset_folder"
	return parent_dir + "/materials/" + material_name + ".tres"

# get the base directory from a path
func _get_base_dir(path: String) -> String:
	var idx = path.rfind("/")
	if idx == -1:
		return ""
	return path.substr(0, idx)
