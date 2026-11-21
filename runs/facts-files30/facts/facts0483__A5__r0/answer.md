

<evidence>
[E1] "Researchers narrow in on the local network and how IoT devices can inadvertently compromise consumer privacy through the exposure of sensitive data within those local networks using standard protocols such as UPnP or mDNS. Researchers say this essentially allows nearly any company to learn what devices are in a home, when the user is home, and where the home is." (doc.txt)
[E2] "According to the paper, these threats include the exposure of unique device names, UUIDs, and even household geolocation data, all of which can be harvested by companies involved in surveillance capitalism without user awareness." (doc.txt)
[E3] "These local network protocols can be employed as side-channels to access data that is supposedly protected by several mobile app permissions such as household locations, researchers say." (doc.txt)
[E4] "Narseo Vallina-Rodriguez, Associate Research Professor of IMDEA Networks and co-founder of AppCensus, says in a statement that side channels are a sneaky way of indirectly accessing sensitive data." (doc.txt)
[E5] "“For example, Android app developers are supposed to request and obtain users’ consent to access data like geolocation,” Vallina-Rodriguez says. “However, we have shown that certain spyware apps and advertising companies do abuse local network protocols to silently access such sensitive information without any user awareness. All they have to do is kindly ask for it to other IoT devices deployed in the local network using standard protocols like UPnP.”" (doc.txt)
[E6] "In addition, Juan Tapiador, professor at Universidad Carlos III de Madrid, says the study shows that local network protocols used by IoT devices are not sufficiently protected and expose sensitive information about the home and the homeowners’ use of the devices." (doc.txt)
[E7] "“This information is being collected in an opaque way and makes it easier to create profiles of our habits or socioeconomic level,” Tapiador says." (doc.txt)
[E8] "In other comments, Dr. Joel Reardon, PhD, associate professor of computer science at the University of Calgary, says the research shows the home network is not as secure as once thought." (doc.txt)
[E9] "“If a new phone connects to a network, then all the apps on it can have direct access to everything else on that network,” Reardon says. “The spyware I found in apps with tens of millions of installs was in fact scanning networks and talking to routers.”" (doc.txt)
</evidence>
<answer>
**What the document actually covers vs. what it does not**

- **Browsing history, financial transactions, and health issues:** The document does not mention these specific categories at all. What it does describe is that IoT devices expose other kinds of sensitive data on local networks — "unique device names, UUIDs, and even household geolocation data" [E2] — which "essentially allows nearly any company to learn what devices are in a home, when the user is home, and where the home is" [E1]. It also notes this data "makes it easier to create profiles of our habits or socioeconomic level" [E7]. So the document supports the general claim that smart-home devices leak privacy data, but it does not address browsing history, financial transactions, or health issues specifically.

**How the "tapping into the wifi" mechanism works (per the document)**

The mechanism is local network protocols such as UPnP and mDNS, which the researchers call "side-channels" [E1, E3]. As Vallina-Rodriguez explains, app developers are "supposed to request and obtain users’ consent" for data like geolocation, but "certain spyware apps and advertising companies do abuse local network protocols to silently access such sensitive information without any user awareness. All they have to do is kindly ask for it to other IoT devices deployed in the local network using standard protocols like UPnP" [E5]. Reardon adds that "if a new phone connects to a network, then all the apps on it can have direct access to everything else on that network," and that the spyware he found "was in fact scanning networks and talking to routers" [E9].

**On a connected device controlling all other devices without consent**

I can't offer a personal opinion, but the document does contain the researchers' assessments, which are strongly negative: Vallina-Rodriguez calls side channels "a sneaky way of indirectly accessing sensitive data" [E4]; Tapiador says the protocols "are not sufficiently protected and expose sensitive information about the home and the homeowners’ use of the devices," collected "in an opaque way" [E6, E7]; and Reardon concludes "the home network is not as secure as once thought" [E8]. One precision: the document says a connected device's apps get "direct access to everything else on that network" [E9] — it describes access, and does not explicitly state that the device can *control* the other devices.
</answer>