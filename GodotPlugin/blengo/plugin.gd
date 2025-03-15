@tool
extends EditorPlugin

var Blengo_Menu: MenuButton

# UI menu
func _enter_tree():
	Blengo_Menu = MenuButton.new()
	Blengo_Menu.text = "#BlenGo"
	Blengo_Menu.add_theme_color_override("font_color", Color8(255, 165, 0))
	var popup = Blengo_Menu.get_popup()
	popup.add_item("Set Properties", 1)
	popup.add_item("About", 2)
	popup.connect("id_pressed", Callable(self, "_on_menu_item_pressed"))
	add_control_to_container(EditorPlugin.CONTAINER_TOOLBAR, Blengo_Menu)

func _exit_tree():
	remove_control_from_container(EditorPlugin.CONTAINER_TOOLBAR, Blengo_Menu)
	Blengo_Menu.free()

func _on_menu_item_pressed(id: int) -> void:
	match id:
		1:
			var glb_file_finder_script = load("res://addons/blengo/scripts/GLBFileFinder.gd")
			if glb_file_finder_script:
				var glb_file_finder_instance = glb_file_finder_script.new()
				# Ensure the instance has the 'execute' method
				if glb_file_finder_instance and glb_file_finder_instance.has_method("execute"):
					glb_file_finder_instance.execute(get_editor_interface())
				else:
					print("Failed to instantiate GLBFileFinder script or 'execute' method not found.")
			else:
				print("Failed to load GLBFileFinder.gd")
		2:
			print("About menu selected")
			OS.shell_open("https://github.com/PanPanwastaken/BlenGo")
