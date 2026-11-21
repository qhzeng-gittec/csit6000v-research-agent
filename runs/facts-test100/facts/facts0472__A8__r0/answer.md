

Based on `doc.txt`, the 3D pipeline consists of the following stages:

1. **Vertex Fetch (VF) Stage** — "The VF stage executes 3DPRIMITIVE commands. Some enhancements have been included to better support legacy D3D APIs as well as SGI OpenGL*." (doc.txt)

2. **Vertex Shader (VS) Stage** — "The VS stage performs shading of vertices output by the VF function. The VS unit produces an output vertex reference for every input vertex reference received from the VF unit, in the order received." (doc.txt)

3. **Geometry Shader (GS) Stage** — "The GS stage receives inputs from the VS stage. Compiled application-provided GS programs, specifying an algorithm to convert the vertices of an input object into some output primitives." (doc.txt) Examples given: a GS shader "may convert lines of a line strip into polygons representing a corresponding segment of a blade of grass centered on the line," or "use adjacency information to detect silhouette edges of triangles and output polygons extruding out from the edges." (doc.txt)

4. **Clip Stage** — "The Clip stage performs general processing on incoming 3D objects. However, it also includes specialized logic to perform a Clip Test function on incoming objects. The Clip Test optimizes generalized 3D Clipping. The Clip unit examines the position of incoming vertices, and accepts/rejects 3D objects based on its Clip algorithm." (doc.txt)

5. **Strips and Fans (SF) Stage** — "The SF stage performs setup operations required to rasterize 3D objects. The outputs from the SF stage to the Windower stage contain implementation-specific information required for the rasterization of objects and also supports clipping of primitives to some extent." (doc.txt)

6. **Windower/IZ (WIZ) Stage** — "The WIZ unit performs an early depth test, which removes failing pixels and eliminates unnecessary processing overhead." (doc.txt) It also does the rasterization: "The Windower uses the parameters provided by the SF unit in the object-specific rasterization algorithms. The WIZ unit rasterizes objects into the corresponding set of pixels." (doc.txt) Additionally, "The Windower is also capable of performing dithering, whereby the illusion of a higher resolution when using low-bpp channels in color buffers is possible. Color dithering diffuses the sharp color bands seen on smooth-shaded objects." (doc.txt)

The document also notes related non-3D units: the Video Engine "handles the non-3D (media/video) applications. It includes support for VLD and MPEG2 decode in hardware." (doc.txt), and the 2D Engine "contains BLT (Block Level Transfer) functionality and an extensive set of 2D instructions. To take advantage of the 3D during engine's functionality, some BLT functions make use of the 3D renderer." (doc.txt)