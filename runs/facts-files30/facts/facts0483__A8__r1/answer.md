

Based solely on `doc.txt`, here is what the document does and does not cover:

**What the document does not address:** The document does not mention browsing history, financial transactions, or health issues at all. It also does not discuss a device "controlling" other devices, and it offers no opinion on the consent issue you raise.

**How the Wi-Fi/local-network mechanism works, per the document:**

- The research (a paper titled "In the Room Where It Happens: Characterizing Local Communication and Threats in Smart Homes") "narrow[s] in on the local network and how IoT devices can inadvertently compromise consumer privacy through the exposure of sensitive data within those local networks using standard protocols such as UPnP or mDNS," which "essentially allows nearly any company to learn what devices are in a home, when the user is home, and where the home is" (doc.txt).
- The exposed data includes "unique device names, UUIDs, and even household geolocation data, all of which can be harvested by companies involved in surveillance capitalism without user awareness" (doc.txt).
- The protocols act as side-channels: "These local network protocols can be employed as side-channels to access data that is supposedly protected by several mobile app permissions such as household locations" (doc.txt). One researcher explained: "we have shown that certain spyware apps and advertising companies do abuse local network protocols to silently access such sensitive information without any user awareness. All they have to do is kindly ask for it to other IoT devices deployed in the local network using standard protocols like UPnP" (doc.txt).
- On the "just tapping into the wifi" part, the document says: "If a new phone connects to a network, then all the apps on it can have direct access to everything else on that network," and "The spyware I found in apps with tens of millions of installs was in fact scanning networks and talking to routers" (doc.txt).

So the document's account is that once an app is on the local Wi-Fi network, it can query the other devices on that network with standard protocols (UPnP/mDNS) and harvest identifying data and location information without user consent — but it does not describe access to browsing history, financial transactions, or health data, and it does not state that devices can control one another.