

Based on `doc.txt`, the 3D pipeline consists of the following stages:

1. **Vertex Fetch (VF) Stage** – Executes 3DPRIMITIVE commands, with enhancements to support legacy D3D APIs and SGI OpenGL.

2. **Vertex Shader (VS) Stage** – Performs shading of the vertices output by the VF function. The VS unit produces an output vertex reference for every input vertex reference received from the VF unit, in the order received.

3. **Geometry Shader (GS) Stage** – Receives inputs from the VS stage. Compiled application-provided GS programs specify an algorithm to convert the vertices of an input object into output primitives. For example, a GS shader may convert lines of a line strip into polygons (e.g., a segment of a blade of grass centered on the line), or use adjacency information to detect silhouette edges of triangles and output polygons extruding from the edges.

4. **Clip Stage** – Performs general processing on incoming 3D objects, and includes specialized logic for a Clip Test function that optimizes generalized 3D clipping. The Clip unit examines the position of incoming vertices and accepts/rejects 3D objects based on its Clip algorithm.

5. **Strips and Fans (SF) Stage** – Performs setup operations required to rasterize 3D objects. Its outputs to the Windower stage contain implementation-specific information needed for rasterization, and it also supports clipping of primitives to some extent.

6. **Windower/IZ (WIZ) Stage** – Performs an early depth test, removing failing pixels and eliminating unnecessary processing overhead. The Windower uses parameters provided by the SF unit in object-specific rasterization algorithms, and the WIZ unit rasterizes objects into the corresponding set of pixels. The Windower can also perform dithering, creating the illusion of higher resolution when using low-bpp channels in color buffers; color dithering diffuses the sharp color bands seen on smooth-shaded objects.

The document also notes that the 3D Engine block diagram includes a Clipper, Strip & Fan/Setup, Geometry Shader, and Vertex Fetch/Vertex Shader, and that some 2D BLT functions make use of the 3D renderer.