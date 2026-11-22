

The document in `doc.txt` covers parts of this question, but several of the premises in the question are not supported by it. Here is what the document actually states:

**How Zero Trust works (its security model)**

- "Zero trust is based on the premise "Never trust, always verify," which means that no user or machine is granted access (trust) until they are authorized." (doc.txt)
- "Zero trust is founded on the principle that no person or device should be granted system access based on inherent trust." (doc.txt)
- "Instead, zero trust assumes that the network has already been compromised. Therefore, no user or device can access systems or assets without first being authorized via strong authentication methods like MFA (multi-factor authentication)." (doc.txt)
- "As an added security measure, users are continuously verified even after their initial authorization." (doc.txt)

**How Zero Trust mitigates ransomware**

The document says zero trust is "designed to severely limit the damage that ransomware and other cyberattacks can cause" and that it "Prevents attackers from gaining easy access to critical applications" and "severely curtails their ability to cause damage if they do get in." (doc.txt) Specifically, "When zero trust is implemented:" (doc.txt)

- "Ransomware attackers are blocked from accessing critical applications." (doc.txt)
- "Ransomware attackers are prevented from moving laterally, mitigating their ability to access and leak data." (doc.txt)
- "Ransomware attackers cannot see the different system components, target them and gain a foothold." (doc.txt)
- "Auditing and recording capabilities help detect breaches and prevent further damage." (doc.txt)
- "The network is hidden, preventing attack methods like IP scanning." (doc.txt)
- "Potentially vulnerable VPNs are enhanced by adding an extra layer of security." (doc.txt)

**ZTNA vs. VPNs**

- "Many organizations use VPNs to secure their critical applications, especially when providing access for remote users and third parties like partners and contractors." (doc.txt)
- "However, VPNs are not secure. First, VPNs provide external users with too much access. Any authenticated user has access to the entire network, including databases and infrastructure. In addition, VPNs providers often have major security vulnerabilities - as recent security incidents such as the Solar Winds cyberattack have demonstrated." (doc.txt)

**What the document does not support**

- The document does not say Zero Trust "eliminates" VPNs or renders them "irrelevant" for external or internal connections. To the contrary, it states that "Potentially vulnerable VPNs are enhanced by adding an extra layer of security." (doc.txt)
- The document does not say Zero Trust "does not allow any ransomware in the first place"; it says zero trust "severely limit[s] the damage" and "severely curtails their ability to cause damage if they do get in." (doc.txt)
- The document does not state that Zero Trust "requires no extra measures like encryption or network segmentation," and it does not use the phrase "maximum security assurance." These claims are not addressed in the document.