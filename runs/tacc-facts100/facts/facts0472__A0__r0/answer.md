

Based on `doc.txt`, the 3D pipeline consists of the following stages:

1. **Vertex Fetch (VF) Stage** – Executes 3DPRIMITIVE commands, with enhancements included to better support legacy D3D APIs and SGI OpenGL.

2. **Vertex Shader (VS) Stage** – Performs shading of the vertices output by the VF stage. The VS unit produces an output vertex reference for every input vertex reference received from the VF unit, in the order received.

3. **Geometry Shader (GS) Stage** – Receives inputs from the VS stage. Compiled application-provided GS programs specify an algorithm to convert the vertices of an input object into output primitives. For example, a GS shader may convert lines of a line strip into polygons (e.g., a segment of a blade of grass centered on the line), or use adjacency information to detect silhouette edges of triangles and output polygons extruding from those edges.

4. **Clip Stage** – Performs general processing on incoming 3D objects, and includes specialized logic for a Clip Test function that optimizes generalized 3D clipping. The Clip unit examines the position of incoming vertices and accepts/rejects 3D objects based on its Clip algorithm.

5. **Strips and Fans (SF) Stage** – Performs the setup operations required to rasterize 3D objects. Its outputs to the Windower stage contain implementation-specific information needed for rasterization, and it also supports clipping of primitives to some extent.

6. **Windower/IZ (WIZ) Stage** – Performs an early depth test, removing failing pixels and eliminating unnecessary processing overhead. The Windower uses parameters provided by the SF unit in object-specific rasterization algorithms to rasterize objects into the corresponding set of pixels. It is also capable of dithering, which creates the illusion of higher resolution when using low-bpp color channels and diffuses sharp color bands on smooth-shaded objects.

The document also notes that the overall graphics controller includes a **Video Engine** (handling non-3D media/video applications, with hardware VLD and MPEG2 decode) and a **2D Engine** (with BLT block-transfer functionality and 2D instructions, some of which make use of the 3D renderer), but these are separate from the 3D pipeline stages listed above.