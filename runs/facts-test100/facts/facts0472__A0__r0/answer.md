

Based on `doc.txt`, the 3D pipeline consists of the following stages:

1. **Vertex Fetch (VF) Stage** – Executes 3DPRIMITIVE commands, with enhancements included to better support legacy D3D APIs and SGI OpenGL.

2. **Vertex Shader (VS) Stage** – Performs shading of the vertices output by the VF stage. The VS unit produces an output vertex reference for every input vertex reference received from the VF unit, in the order received.

3. **Geometry Shader (GS) Stage** – Receives inputs from the VS stage and runs compiled application-provided GS programs that convert the vertices of an input object into output primitives. Examples given: converting lines of a line strip into polygons (e.g., a segment of a blade of grass centered on the line), or using adjacency information to detect silhouette edges of triangles and output polygons extruding from the edges.

4. **Clip Stage** – Performs general processing on incoming 3D objects, and includes specialized logic for a Clip Test function that optimizes generalized 3D clipping. The Clip unit examines the position of incoming vertices and accepts or rejects 3D objects based on its Clip algorithm.

5. **Strips and Fans (SF) Stage** – Performs the setup operations required to rasterize 3D objects. Its outputs to the Windower stage contain implementation-specific information needed for rasterization, and it also supports clipping of primitives to some extent.

6. **Windower/IZ (WIZ) Stage** – Performs an early depth test that removes failing pixels and eliminates unnecessary processing overhead. The Windower uses parameters provided by the SF unit in object-specific rasterization algorithms, and rasterizes objects into the corresponding set of pixels. It can also perform dithering, creating the illusion of higher resolution when using low-bpp color buffer channels, and diffuses the sharp color bands seen on smooth-shaded objects.

The document also notes related (non-3D) units: the **Video Engine** (handles media/video applications, with hardware support for VLD and MPEG2 decode) and the **2D Engine** (provides BLT block-transfer functionality and 2D instructions, with some BLT functions making use of the 3D renderer).