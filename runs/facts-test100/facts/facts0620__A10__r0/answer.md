

The document in `doc.txt` does not support several premises in your question, so I'll answer what it does say and flag what it does not.

**How Zero Trust provides security assurance (per the document):**

- "Zero trust is a modern and innovative security model designed to severely limit the damage that ransomware and other cyberattacks can cause." (doc.txt)
- "By never inherently trusting users or devices and instead continuously verifying them before granting access, the zero trust framework: Prevents attackers from gaining easy access to critical applications And severely curtails their ability to cause damage if they do get in." (doc.txt)
- "Zero trust is based on the premise "Never trust, always verify," which means that no user or machine is granted access (trust) until they are authorized." (doc.txt)
- "zero trust assumes that the network has already been compromised. Therefore, no user or device can access systems or assets without first being authorized via strong authentication methods like MFA (multi-factor authentication)." (doc.txt)
- "As an added security measure, users are continuously verified even after their initial authorization." (doc.txt)
- When zero trust is implemented: "Ransomware attackers are blocked from accessing critical applications." / "Ransomware attackers are prevented from moving laterally, mitigating their ability to access and leak data." / "Ransomware attackers cannot see the different system components, target them and gain a foothold." / "Auditing and recording capabilities help detect breaches and prevent further damage." / "The network is hidden, preventing attack methods like IP scanning." (doc.txt)

**How it surpasses VPNs (per the document):**

- "Many organizations use VPNs to secure their critical applications, especially when providing access for remote users and third parties like partners and contractors." (doc.txt)
- "However, VPNs are not secure. First, VPNs provide external users with too much access. Any authenticated user has access to the entire network, including databases and infrastructure. In addition, VPNs providers often have major security vulnerabilities - as recent security incidents such as the Solar Winds cyberattack have demonstrated." (doc.txt)

**What the document does NOT say:**

- It does not state that Zero Trust "eliminates traditional VPNs" or renders them "irrelevant for external connections and internal connections." To the contrary, it says "Potentially vulnerable VPNs are enhanced by adding an extra layer of security." (doc.txt) — i.e., VPNs are enhanced, not eliminated.
- It does not claim Zero Trust works "by not allowing any ransomware in the first place"; it says it "severely limit[s] the damage" and that "Zero trust access policies prevent the spread of ransomware." (doc.txt)
- It does not state that Zero Trust "requires no extra measures like encryption or network segmentation." The document does not address whether encryption or network segmentation are required or unnecessary.