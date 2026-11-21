Based only on `doc.txt`, here is what the document does and does not say:

**What the document does not cover:** The document does not mention spying on people's browsing history, financial transactions, or health issues. It also does not say that a connected device can "control all of the other devices without consent." I cannot offer an opinion on that claim, and the document does not address it.

**What the document does say about how this works:**

The article describes research (the paper "In the Room Where It Happens: Characterizing Local Communication and Threats in Smart Homes") on local network interactions between 93 IoT devices and their mobile apps. The mechanism is that local network protocols are not sufficiently protected:

- "Researchers narrow in on the local network and how IoT devices can inadvertently compromise consumer privacy through the exposure of sensitive data within those local networks using standard protocols such as UPnP or mDNS." (doc.txt)
- "According to the paper, these threats include the exposure of unique device names, UUIDs, and even household geolocation data, all of which can be harvested by companies involved in surveillance capitalism without user awareness." (doc.txt)
- "These local network protocols can be employed as side-channels to access data that is supposedly protected by several mobile app permissions such as household locations, researchers say." (doc.txt)

On how apps bypass app-permission protections by tapping into the local network:

- "However, we have shown that certain spyware apps and advertising companies do abuse local network protocols to silently access such sensitive information without any user awareness. All they have to do is kindly ask for it to other IoT devices deployed in the local network using standard protocols like UPnP." (doc.txt)
- "If a new phone connects to a network, then all the apps on it can have direct access to everything else on that network," says Dr. Joel Reardon. "The spyware I found in apps with tens of millions of installs was in fact scanning networks and talking to routers." (doc.txt)

So, per the document, the "bypass" works because once a device (e.g., a phone) is on the local network, its apps can directly access everything else on that network and query other IoT devices via standard protocols like UPnP, silently obtaining data that app permissions were supposed to protect — but the specific data types you listed (browsing history, financial transactions, health issues) and the claim of controlling other devices are not in the document.