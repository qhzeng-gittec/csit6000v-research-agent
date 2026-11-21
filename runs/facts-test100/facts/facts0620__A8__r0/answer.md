

The document does not support the premises of your question, so I'll first flag those, then answer the parts the document actually covers.

**Premises the document does not state**

- The document does not say zero trust works "by not allowing any ransomware in the first place." It says zero trust is "designed to severely limit the damage that ransomware and other cyberattacks can cause" (doc.txt), and that "Zero trust access policies prevent the spread of ransomware" (doc.txt) — i.e., it limits spread and damage, not that ransomware is never allowed in.
- The document does not say zero trust "requires no extra measures like encryption or network segmentation." It does not discuss encryption or network segmentation at all. To the contrary, it lists among zero trust's effects that "Potentially vulnerable VPNs are enhanced by adding an extra layer of security" (doc.txt).

**How the document says zero trust provides security assurance**

- It is "based on the premise 'Never trust, always verify,' which means that no user or machine is granted access (trust) until they are authorized" (doc.txt).
- "Zero trust assumes that the network has already been compromised. Therefore, no user or device can access systems or assets without first being authorized via strong authentication methods like MFA (multi-factor authentication)" (doc.txt).
- "As an added security measure, users are continuously verified even after their initial authorization" (doc.txt).
- When implemented: "Ransomware attackers are blocked from accessing critical applications." "Ransomware attackers are prevented from moving laterally, mitigating their ability to access and leak data." "Ransomware attackers cannot see the different system components, target them and gain a foothold." "Auditing and recording capabilities help detect breaches and prevent further damage." "The network is hidden, preventing attack methods like IP scanning." (doc.txt)
- Operationally, it secures the domains of "Data," "People," "Devices," "Networks," and "Workloads" via ZTNA, which "is a software perimeter that applies the zero trust principles when authorizing users and services" (doc.txt).

**How the document says it surpasses VPNs**

- "However, VPNs are not secure. First, VPNs provide external users with too much access. Any authenticated user has access to the entire network, including databases and infrastructure. In addition, VPNs providers often have major security vulnerabilities - as recent security incidents such as the Solar Winds cyberattack have demonstrated" (doc.txt).

**What the document does not address**

- The document does not state that VPNs are "rendered irrelevant for external connections and internal connections." It does not use that framing; instead it says "Potentially vulnerable VPNs are enhanced by adding an extra layer of security" (doc.txt), implying VPNs can remain in use with zero trust layered on top. It also does not make any claim about "maximum security assurance" as such, nor does it address internal connections specifically.