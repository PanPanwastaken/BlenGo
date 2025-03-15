@tool
extends Node

var file_dialog: FileDialog
var editor_interface: EditorInterface
signal glb_selected(path)

func execute(editor_interface: EditorInterface) -> void:
	self.editor_interface = editor_interface  # Save for later use
	# Create the file dialog.
	file_dialog = FileDialog.new()
	file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	file_dialog.title = "Select a GLB File"
	file_dialog.filters = ["*.glb ; GLB Files"]
	
	# Connect the file selection signal
	file_dialog.connect("file_selected", Callable(self, "_on_file_selected"))
	editor_interface.get_base_control().add_child(file_dialog)
	file_dialog.popup_centered()

# Triggered after the user selects a file
func _on_file_selected(selected_file: String) -> void:
	print("Selected GLB file: ", selected_file)
	var entries = _process_glb_file(selected_file)
	file_dialog.queue_free()
	# Pass the selected file path along with the data
	_display_data_in_menu(entries, selected_file)

# Process the GLB file and extract JSON data
func _process_glb_file(file_path: String) -> Array:
	var entries = []
	var file = FileAccess.open(file_path, FileAccess.READ)
	if not file:
		print("Failed to open file: ", file_path)
		return entries
	var glb_data = file.get_buffer(file.get_length())
	file.close()

	# Validate GLB magic
	var magic = glb_data.slice(0, 4).get_string_from_utf8()
	if magic != "glTF":
		print("Invalid GLB file: ", file_path)
		return entries

	# Extract JSON chunk length
	var buffer = StreamPeerBuffer.new()
	buffer.data_array = glb_data
	buffer.seek(12)  # Byte offset for JSON chunk length
	var json_chunk_length = buffer.get_u32()
	print("JSON Chunk Length: ", json_chunk_length)

	# Extract JSON chunk data
	var json_chunk_data = glb_data.slice(20, 20 + json_chunk_length)
	var json_string = json_chunk_data.get_string_from_utf8().strip_edges()

	# Parse the JSON string
	var json_parser = JSON.new()
	var error = json_parser.parse(json_string)
	if error != OK:
		print("Error parsing JSON in: ", file_path, " - Error code: ", error)
		return entries

	# Retrieve the parsed JSON data
	var json_data = json_parser.get_data()

	# Process materials, objects, and meshes separately
	entries.append_array(_process_materials(json_data))
	entries.append_array(_process_objects(json_data))
	entries.append_array(_process_meshes(json_data))
	return entries

# Process materials from the JSON data
func _process_materials(json_data: Dictionary) -> Array:
	var material_entries = []
	if json_data.has("scenes"):
		for scene in json_data["scenes"]:
			if scene.has("extras") and scene["extras"].has("godot_material_metadata"):
				var material_metadata_json = scene["extras"]["godot_material_metadata"]
				var material_parser = JSON.new()
				var material_error = material_parser.parse(material_metadata_json)
				if material_error == OK:
					for material_name in material_parser.get_data().keys():
						var material_props = material_parser.get_data()[material_name]
						for prop_key in material_props.keys():
							if prop_key.begins_with("blengo_"):
								material_entries.append({
									"Type": "Material",
									"Name": material_name,
									"Property": material_props[prop_key]
								})
	return material_entries

# Process objects from the JSON data
func _process_objects(json_data: Dictionary) -> Array:
	var object_entries = []
	if json_data.has("nodes"):
		for node in json_data["nodes"]:
			if node.has("extras"):
				var extras = node["extras"]
				for key in extras.keys():
					if key.begins_with("blengo_"):
						object_entries.append({
							"Type": "Object",
							"Name": node.get("name", "Unknown"),
							"Property": extras[key]
						})
						break
	return object_entries

# Process meshes from the JSON data
func _process_meshes(json_data: Dictionary) -> Array:
	var mesh_entries = []
	if json_data.has("meshes"):
		for mesh in json_data["meshes"]:
			if mesh.has("extras"):
				var extras = mesh["extras"]
				for key in extras.keys():
					if key.begins_with("blengo_"):
						mesh_entries.append({
							"Type": "Mesh",
							"Name": mesh.get("name", "Unknown"),
							"Property": extras[key]
						})
						break
	return mesh_entries

# Open the PropertyProcessMenu window and pass the data along with the file path
func _display_data_in_menu(entries: Array, file_path: String) -> void:
	var menu_scene = load("res://addons/blengo/menus/PropertyProcessMenu.tscn")
	if menu_scene:
		var menu_instance = menu_scene.instantiate()
		var data_string = ""
		for entry in entries:
			data_string += "Type: " + str(entry["Type"]) + ", Name: " + str(entry["Name"]) + ", Property: " + str(entry["Property"]) + "\n"
		# Defer the call so that onready variables in menu_instance are properly set
		menu_instance.call_deferred("set_data", data_string, file_path)
		if editor_interface and editor_interface.get_base_control():
			editor_interface.get_base_control().add_child(menu_instance)
			menu_instance.popup_centered()
		else:
			print("Editor interface or base control is not available.")
	else:
		print("Failed to load PropertyProcessMenu.tscn")
