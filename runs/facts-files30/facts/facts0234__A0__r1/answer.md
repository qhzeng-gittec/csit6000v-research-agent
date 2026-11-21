

Based solely on `doc.txt` (a NIST SP 800-215 excerpt on the enterprise network landscape), the enhanced firewall capabilities described in the "Enhanced Firewall Capabilities" and "Appliance-set with Integrated Functions" sections benefit network security in the following ways:

**Visibility and inspection of traffic**
- Packet filtering and NAT monitor and control packets crossing a network interface, apply predetermined security rules, and obscure the internal network from the public internet.
- Stateful inspection tracks the state of connections so only packets belonging to a known active connection are allowed through.
- Deep packet inspection (DPI) examines both packet headers and payloads, enabling the detection of hidden threats in the data stream such as data exfiltration attempts, content policy violations, and malware.
- Next-generation firewalls add application data awareness (OSI layer 7), TLS decryption, and payload inspection, going beyond basic packet filtering.

**Threat detection, response, and prevention**
- Modern firewalls gather and analyze data across multiple packets and sessions to detect threats and security incidents targeting a particular system or family of systems.
- Data from multiple firewalls can be sent to a SIEM and correlated with other security tools to detect enterprise-wide attacks spanning multiple systems and network layers, and to understand evolving threats, define new access rules, attack patterns, and defensive strategies.
- Web application firewalls detect traffic from malicious URLs (using real-time machine-learning-analyzed data), inspect threat vectors such as SQL injection, OS command injection, and cross-site scripting, prevent inbound attacks, and help prevent DDoS attacks in CDNs.
- Intrusion prevention, bot defense, and API protection (WAAP) add further defense layers.

**Control of access and policy**
- Access control functions enforce granular, sophisticated access control policies.
- Policy composition allows merging policies at enforcement time so consistent policies apply to different user classes (on-premises and on private and public clouds).
- Secure web gateways provide policy-based access to cloud applications, govern access to the open web, inspect outbound HTTP/HTTPS traffic, and protect endpoints from web-based threats such as malicious links and malware-infected websites.

**Network segmentation and layered defense**
- Firewalls at the network edge protect the perimeter by filtering disallowed sources and destinations and blocking packets of potential threats.
- Firewalls inside a data center segment the internal network to prevent lateral movement of traffic and isolate sensitive resources (services and data stores).
- Device-based firewalls prevent malicious traffic in and out of endpoints.

**Operations, management, and extensibility**
- Logging and auditing construct records of network events that reveal patterns of performance and security issues.
- Open APIs enable integration with other networking products that add security capabilities.
- Unified threat management devices combine firewall, IPS, VPN, gateway antivirus, content filtering, and WAN load balancing into a single device with a unified management console, simplifying management.

In short, according to the document, as firewalls have evolved from simple perimeter packet blockers, their enhanced capabilities improve network security by providing deeper inspection (including encrypted and application-level traffic), proactive threat detection and correlation across the enterprise, granular and consistent access control, segmentation to limit lateral movement, endpoint and web-application protection, and better visibility, management, and integration.