BlenGo is our team's solution for bridging the gap between Blender and Godot. It allows us to design levels predominantly in Blender while addressing common workflow issues—such as root motion rotation and animation glitches. Leveraging the GLTF format's support for custom properties in metadata and its ability to maintain linked Blender instances, it opens up endless possibilities for efficient Level Design.

Key Features
Godot Suffix Tool:
Provides a comprehensive menu of Godot-specific suffixes used during the import process. Each suffix comes with a brief explanation of its function, ensuring you understand its impact on your workflow.

Collision Shapes:
Automatically generates a collision mesh for objects using the -colonly suffix. This simplifies the creation and assignment of collision shapes.

Asset Folder Setup:
Creates an asset folder named after your Blender file. This feature organizes your project by automatically setting up dedicated folders for textures, scenes, and materials, and it can directly export all textures into the corresponding texture folder.

Scene Export:
Uses Blender’s GLTF exporter to generate scenes. You can create custom export presets to tailor the process to your specific needs.

Texture Export:
Exports textures with built-in rescaling options, ensuring your assets are optimized and correctly sized.

Custom Material Properties:
Embeds custom material properties within metadata to assign external materials directly in Godot, streamlining the material management process.

Custom Object Properties:
Adds additional object properties for operations and settings that go beyond what Godot's suffix system supports, offering more flexibility in asset handling.

Below are some screenshots showcasing BlenGo in action:

![image](https://github.com/user-attachments/assets/59bcd1a1-aa8e-4afd-8222-a05c2d076323)
Assigning Godot Shaders when imported:
![image](https://github.com/user-attachments/assets/215fbf49-bc20-423f-ae79-42330fe2476e)

Note: the addon is still exprimental, I will add more features as our project goes on.
