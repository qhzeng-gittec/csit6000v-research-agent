Based on `doc.txt`, the 3D pipeline consists of the following stages:

1. **Vertex Fetch (VF) Stage** — "The VF stage executes 3DPRIMITIVE commands. Some enhancements have been included to better support legacy D3D APIs as well as SGI OpenGL*."

2. **Vertex Shader (VS) Stage** — "The VS stage performs shading of vertices output by the VF function. The VS unit produces an output vertex reference for every input vertex reference received from the VF unit, in the order received."

3. **Geometry Shader (GS) Stage** — "The GS stage receives inputs from the VS stage. Compiled application-provided GS programs, specifying an algorithm to convert the vertices of an input object into some output primitives." Examples given: converting "lines of a line strip into polygons representing a corresponding segment of a blade of grass centered on the line," or using "adjacency information to detect silhouette edges of triangles and output polygons extruding out from the edges."

4. **Clip Stage** — "The Clip stage performs general processing on incoming 3D objects. However, it also includes specialized logic to perform a Clip Test function on incoming objects. The Clip Test optimizes generalized 3D Clipping. The Clip unit examines the position of incoming vertices, and accepts/rejects 3D objects based on its Clip algorithm."

5. **Strips and Fans (SF) Stage** — "The SF stage performs setup operations required to rasterize 3D objects. The outputs from the SF stage to the Windower stage contain implementation-specific information required for the rasterization of objects and also supports clipping of primitives to some extent."

6. **Windower/IZ (WIZ) Stage** — "The WIZ unit performs an early depth test, which removes failing pixels and eliminates unnecessary processing overhead." It also "rasterizes objects into the corresponding set of pixels" and "is also capable of performing dithering, whereby the illusion of a higher resolution when using low-bpp channels in color buffers is possible. Color dithering diffuses the sharp color bands seen on smooth-shaded objects."

Regarding "compiling" specifically, the document only mentions compilation in the GS stage, referring to "Compiled application-provided GS programs"; it does not describe a separate compilation stage for the pipeline as a whole.