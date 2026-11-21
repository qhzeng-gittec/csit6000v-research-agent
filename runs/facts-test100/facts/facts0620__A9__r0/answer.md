

Based on `doc.txt`, here is what the document states, and where it does not support the premises in your question.

**How Zero Trust provides security assurance (per the document):**
- Zero trust is based on the premise "Never trust, always verify" — no user or machine is granted access (trust) until they are authorized.
- It assumes the network has already been compromised, so no user or device can access systems or assets without first being authorized via strong authentication methods like MFA (multi-factor authentication).
- Users are continuously verified even after their initial authorization.
- When zero trust is implemented, it mitigates ransomware by:
  - Blocking ransomware attackers from accessing critical applications.
  - Preventing attackers from moving laterally, mitigating their ability to access and leak data.
  - Preventing attackers from seeing the different system components, targeting them, and gaining a foothold.
  - Using auditing and recording capabilities to help detect breaches and prevent further damage.
  - Hiding the network, preventing attack methods like IP scanning.
  - Enhancing potentially vulnerable VPNs by adding an extra layer of security.

**How it surpasses VPNs (per the document):**
- The document states that "VPNs are not secure."
- VPNs provide external users with too much access: any authenticated user has access to the entire network, including databases and infrastructure.
- VPN providers often have major security vulnerabilities, as demonstrated by recent security incidents such as the SolarWinds cyberattack.

**What the document does NOT support in your question:**
- The document does **not** state that Zero Trust "eliminates traditional VPNs" or renders them "irrelevant." In fact, it says the opposite in one respect: "Potentially vulnerable VPNs are enhanced by adding an extra layer of security."
- The document does **not** say Zero Trust works "by not allowing any ransomware in the first place." It says zero trust "severely limit[s] the damage that ransomware and other cyberattacks can cause," prevents the *spread* of ransomware, and blocks attackers from accessing critical applications — not that it prevents ransomware from entering in the first place.
- The document does **not** discuss encryption or network segmentation as "extra measures," so it neither confirms nor denies that Zero Trust requires or avoids them.
- The document's VPN comparison addresses only **external** users (remote users, partners, contractors). It does **not** discuss internal connections, so it does not state that VPNs are rendered irrelevant for internal connections.