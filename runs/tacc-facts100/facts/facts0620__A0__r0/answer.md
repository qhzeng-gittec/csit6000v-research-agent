

I've read the full `doc.txt` (229 lines). Here is what the document actually says, and where it does and does not support the premises in your question.

## How Zero Trust provides security assurance (per the document)

- **Core premise — "Never trust, always verify":** No user or machine is granted access (trust) until they are authorized. Zero trust assumes the network has *already been compromised*, so no user or device can access systems or assets without first being authorized via strong authentication methods like MFA (multi-factor authentication).
- **Continuous verification:** Users are continuously verified even *after* their initial authorization, not just at login.
- **Effect against ransomware:** When zero trust is implemented, the document lists:
  - Ransomware attackers are blocked from accessing critical applications.
  - Attackers are prevented from moving laterally, mitigating their ability to access and leak data.
  - Attackers cannot see the different system components, target them, and gain a foothold.
  - Auditing and recording capabilities help detect breaches and prevent further damage.
  - The network is hidden, preventing attack methods like IP scanning.
  - Potentially vulnerable VPNs are enhanced by adding an extra layer of security.
- **ZTNA as the implementing technology:** ZTNA (zero trust network access) is described as a "software perimeter" that applies zero trust principles when authorizing users and services, securing the domains of data, people, devices, networks, and workloads.

## How it surpasses VPNs (per the document)

The "ZTNA vs. VPNs" section states that while many organizations use VPNs to secure critical applications for remote users and third parties (partners, contractors), **VPNs are not secure**, for two reasons:
1. **Too much access:** Any authenticated user has access to the *entire network*, including databases and infrastructure — i.e., VPNs give external users far more access than necessary.
2. **Provider vulnerabilities:** VPN providers often have major security vulnerabilities, as demonstrated by incidents such as the SolarWinds cyberattack.

By contrast, zero trust blocks attackers from critical applications, stops lateral movement, hides the network, and adds an extra security layer on top of potentially vulnerable VPNs.

## Where the document does NOT support your question's premises

I must flag that several claims in your question are not in `doc.txt`:

- **"Not allowing any ransomware in the first place"** — The document does not say zero trust prevents ransomware from entering at all. It says zero trust is "designed to *severely limit the damage* that ransomware and other cyberattacks can cause," and that zero trust access policies "prevent the *spread* of ransomware."
- **"Requires no extra measures like encryption or network segmentation"** — The document never makes this claim. It does not discuss network segmentation at all, and it mentions encryption only in the context of ZTNA providers holding customers' "encrypted content" in their cloud.
- **"Maximum security assurance"** — The document does not use this phrase or make a "maximum assurance" claim; it describes zero trust as a model that mitigates ransomware and limits damage.
- **"Rendering VPNs irrelevant for external and internal connections"** — The document does not say VPNs are irrelevant. It says VPNs are not secure (over-broad access, provider vulnerabilities), but it also explicitly states that "potentially vulnerable VPNs are *enhanced* by adding an extra layer of security" under zero trust — i.e., the document frames zero trust as augmenting VPNs, not declaring them obsolete.

So, based solely on `doc.txt`: zero trust's assurance comes from never trusting users/devices, continuous verification with strong authentication (MFA), assuming compromise, blocking access to critical applications, preventing lateral movement, hiding the network, and auditing — and it surpasses VPNs because VPNs grant any authenticated user access to the whole network and carry provider-level vulnerabilities. But the document does not support the specific claims that zero trust blocks all ransomware upfront, needs no encryption/segmentation, or makes VPNs irrelevant.