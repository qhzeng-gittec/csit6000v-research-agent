

Based only on `doc.txt`, here's what the document says — and where it doesn't actually cover your specific examples:

**On browsing history, financial transactions, and health issues:**
The document does not mention these specific categories. It's a summary of a research paper ("In the Room Where It Happens: Characterizing Local Communication and Threats in Smart Homes") about 93 consumer IoT devices and their companion apps. The sensitive data it says is exposed is different: unique device names, UUIDs, unique hardware addresses, and household geolocation data. The researchers say this information "can be pieced together to make a house very identifiable," and that it lets companies "learn what devices are in a home, when the user is home, and where the home is." Professor Juan Tapiador adds that the data "makes it easier to create profiles of our habits or socioeconomic level." So the document describes profiling and location/identity exposure, but not browsing history, financial transactions, or health data specifically.

**How the Wi-Fi "tap" works:**
According to the document, the mechanism is the local network protocols that IoT devices use — specifically **UPnP and mDNS**. These protocols:
- Are "not sufficiently protected" and expose sensitive information about the home and how homeowners use their devices.
- Can act as **side-channels** to access data that is supposedly protected by mobile app permissions (like geolocation).
- Let spyware apps and advertising companies "silently access such sensitive information without any user awareness" — as co-author Narseo Vallina-Rodriguez puts it, "All they have to do is kindly ask for it to other IoT devices deployed in the local network using standard protocols like UPnP."
- Give a newly connected device sweeping access: Dr. Joel Reardon notes, "If a new phone connects to a network, then all the apps on it can have direct access to everything else on that network." He also found spyware in apps with tens of millions of installs that was "scanning networks and talking to routers."

**On the consent concern you raise:**
The document frames this exactly as a consent problem. Vallina-Rodriguez points out that "Android app developers are supposed to request and obtain users' consent to access data like geolocation," yet the research shows apps bypass that by going through the local network instead — a "sneaky way of indirectly accessing sensitive data." Tapiador emphasizes the collection happens "in an opaque way," and Reardon's conclusion is that "the home network is not as secure as once thought." In short, the document's authors treat the ability of one connected device to reach all others without consent as a core, previously undisclosed security flaw in standard local-network protocols, not an acceptable feature.

One caveat: the document is a news summary of the study, so it reports the researchers' findings and quotes rather than technical protocol details beyond naming UPnP and mDNS.