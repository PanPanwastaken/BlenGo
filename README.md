


# BlenGo 
is our team's solution for bridging the gap between Blender and Godot which was needed for our small team to speed up the workflow. It allows us to design levels predominantly in Blender while addressing common workflow issues—such as root motion rotation and animation glitches. Leveraging the GLB format's support for custom properties in metadata and its ability to maintain linked Blender instances, it opens up endless possibilities for efficient Level Design.

Important Note: the addon is still exprimental, I will add more features as our project goes on. The Godot Plugin is under development and will be adeed in the next few days


### Import to Godot in less than a few minutes with all the needed properties:
![Screenshot 2025-03-07 005808](https://github.com/user-attachments/assets/94e7bd1c-2a6f-4c90-a5a7-7dd2f4f401f1)

![image](https://github.com/user-attachments/assets/20a07ecc-5928-4032-a037-5a4e23358bff)


## Key features
### Godot Suffix Tool:
Provides a comprehensive menu of Godot-specific suffixes used during the import process. Each suffix comes with a brief explanation of its function, ensuring you understand its impact on your workflow.

### Collision Shapes:
Automatically generates a collision mesh for objects using the -colonly suffix. This simplifies the creation and assignment of collision shapes.

### Asset Folder Setup:
Creates an asset folder named after your Blender file. This feature organizes your project by automatically setting up dedicated folders for textures, scenes, and materials, and it can directly export all textures into the corresponding texture folder.

### Scene Export:
Uses Blender’s GLTF exporter to generate scenes. You can create custom export presets to tailor the process to your specific needs, keep the effciency of glb while easing the connection of the two softwares.

### Texture Export:
Exports textures with built-in rescaling options, ensuring your assets are optimized and correctly sized.

### Material Export:
Generate Godots BaseMaterial3D (.tres) files with assigned textures directly in blender

### Custom Material Properties:
Embeds custom material properties within metadata to assign custom materials directly in Blender.

### Custom Object Properties:
Adds additional object properties for operations and settings that go beyond what Godot's suffix system supports, offering more flexibility in asset handling. (Mesh Properties for all instances and object Properties for single objects)


