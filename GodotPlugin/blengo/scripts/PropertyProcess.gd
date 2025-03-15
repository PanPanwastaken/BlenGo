@tool
extends Window

# UI Containers
@onready var data_container = $MarginContainer/VBoxContainer/HBoxContainer/VBoxContainer/itemboxcontainer/ItemScrollContainer/VBoxContainer
@onready var cancel_button = $MarginContainer/VBoxContainer/bottombar/cancel_button
@onready var apply_button = $MarginContainer/VBoxContainer/bottombar/apply_button

# Array to store created item containers
var item_containers = []
var file_path : String
var reimporter

func _ready() -> void:
	if cancel_button:
		cancel_button.pressed.connect(self._on_cancel_button_pressed)
	else:
		print("Cancel button not found.")
	if apply_button:
		apply_button.pressed.connect(self._on_apply_button_pressed)
	else:
		print("Apply button not found.")

# This function creates a custom control for one line of data
func create_item(line: String) -> Control:
	# Expecting line format: "Type: <type>, Name: <name>, Property: <property>"
	var parts = line.split(",", false)
	if parts.size() < 3:
		return null  # Not enough parts
		
	var type_text = parts[0].strip_edges()
	var name_text = parts[1].strip_edges()
	var property_text = parts[2].strip_edges()
	
	# Extract the actual type value (remove the "Type:" prefix)
	var type_value = type_text.replace("Type:", "").strip_edges()
	
	var container = HBoxContainer.new()
	
	# Create a CheckButton for toggling
	var check_button = CheckButton.new()
	check_button.set_pressed(true)
	container.add_child(check_button)
	
	# Create a Label for the type portion
	var type_label = Label.new()
	type_label.text = type_text
	type_label.add_theme_color_override("font_color", Color.WHITE_SMOKE)
	container.add_child(type_label)
	
	# Create a Label for the name portion
	var name_label = Label.new()
	name_label.text = name_text
	name_label.add_theme_color_override("font_color", Color.ORANGE)
	container.add_child(name_label)
	
	# Create a Label for the property portion
	var property_label = Label.new()
	property_label.text = property_text
	property_label.add_theme_color_override("font_color", Color.SKY_BLUE)
	container.add_child(property_label)
	
	# Save metadata so we can later retrieve the full text and type
	container.set_meta("check_button", check_button)
	container.set_meta("full_text", line)
	container.set_meta("type", type_value)
	return container

# Called from GLBFileFinder to set the data along with the file path
func set_data(data: String, path: String) -> void:
	file_path = path
	# Instantiate ReImporter and pass the file path
	reimporter = load("res://addons/blengo/scripts/ReImporter.gd").new()
	reimporter.set_file_path(file_path)
	
	var lines = data.split("\n", false)
	for line in lines:
		var trimmed_line = line.strip_edges()
		if trimmed_line == "":
			continue  # Skip blank lines.
		var item = create_item(trimmed_line)
		if item:
			data_container.add_child(item)
			item_containers.append(item)

# Called when the user presses the Apply button
func _on_apply_button_pressed() -> void:
	print("\n=== Processing Items ===")
	for item in item_containers:
		var cb = item.get_meta("check_button")
		if cb and cb.is_pressed():
			var full_text = item.get_meta("full_text")
			var type_value = item.get_meta("type")
			# Delegate processing to ReImporter.
			if type_value == "Material":
				reimporter.process_material_item(full_text)
			elif type_value == "Mesh":
				reimporter.process_mesh_item(full_text)
			elif type_value == "Object":
				reimporter.process_object_item(full_text)
			else:
				print("Unknown type: ", type_value)
	# After processing, close the window
	queue_free()

# Closes the window when Cancel is pressed
func _on_cancel_button_pressed() -> void:
	queue_free()
