

<evidence>
[E1] "The security functions in firewalls have enlarged alongside the changing network landscape." (doc.txt)
[E2] "Packet filtering and Network address translation (NAT) are used to monitor and control packets moving across a network interface, apply predetermined security rules, and obscure the internal network from the public internet." (doc.txt)
[E3] "In addition to the capability provided by stateful inspection, this has capabilities related to finding hidden threats within the data stream, such as attempts at data exfiltration, violations of content policies, malware, and more." (doc.txt)
[E4] "Modern firewalls can gather and analyze enough data across multiple packets and sessions to detect threats and security incidents targeted at a particular system or a family of systems." (doc.txt)
[E5] "These data from multiple firewalls can also be directed toward security information and event management (SIEM) and correlated with data from other security tools and IT systems to detect enterprise-wide attacks that span multiple systems and network layers." (doc.txt)
[E6] "In addition, these data can be used to understand evolving threats and define new access rules, attack patterns, and defensive strategies [6]." (doc.txt)
[E7] "Logging and auditing capabilities result in the construction of network events that can be used to identify patterns of performance and security issues." (doc.txt)
[E8] "Access control functions enforce granular sophisticated access control policies." (doc.txt)
[E9] "Firewalls at the network edge perform the network perimeter protection function by filtering disallowed sources and destinations and blocking the packets of potential threats. Firewalls inside a data center can segment the internal network to prevent the lateral movement of traffic and isolate sensitive resources (e.g., services and data stores). Device-based firewalls prevent malicious traffic in and out of endpoints." (doc.txt)
[E10] "These enable integration with many networking products that provide additional security capabilities." (doc.txt)
[E11] "Some firewalls can have the capabilities to merge policies at enforcement time so as to ensure that consistent policies are applied to different classes of users (e.g., those on-premises and on private and public clouds)." (doc.txt)
[E12] "This is the ability to detect traffic from malicious URLs and prevent web-based threats and attacks by receiving real-time data analyzed by machine learning algorithms [7][8]." (doc.txt)
[E13] "Specifically, this class of firewalls can inspect threat vectors for SQL Injection, operating system (OS) command injections, and cross-site scripting attacks, as well as prevent inbound attacks. They are used in content delivery networks (CDN) and to prevent distributed denial-of-service (DDoS) attacks." (doc.txt)
</evidence>
<answer>
According to doc.txt, firewall security functions have enlarged alongside the changing network landscape [E1], and the enhanced capabilities provide several benefits to network security:

1. **Traffic control and network concealment**: Packet filtering and NAT monitor and control packets across a network interface, apply predetermined security rules, and obscure the internal network from the public internet [E2].

2. **Deeper threat detection**: Deep packet inspection examines both packet headers and payloads, enabling the firewall to find hidden threats in the data stream, such as attempts at data exfiltration, violations of content policies, and malware [E3].

3. **Threat detection and response at scale**: Modern firewalls gather and analyze data across multiple packets and sessions to detect threats and security incidents targeted at a particular system or family of systems [E4]. Data from multiple firewalls can be fed to a SIEM and correlated with other security tools to detect enterprise-wide attacks spanning multiple systems and network layers [E5], and the data can be used to understand evolving threats and define new access rules, attack patterns, and defensive strategies [E6].

4. **Visibility into problems**: Logging and auditing capabilities build network events that help identify patterns of performance and security issues [E7].

5. **Fine-grained access control**: Access control functions enforce granular, sophisticated access control policies [E8].

6. **Protection at multiple locations**: Firewalls at the network edge protect the perimeter by filtering disallowed sources/destinations and blocking packets of potential threats; firewalls inside a data center segment the internal network to prevent lateral movement of traffic and isolate sensitive resources; and device-based firewalls prevent malicious traffic in and out of endpoints [E9].

7. **Extensibility and consistency**: Open APIs enable integration with many networking products that provide additional security capabilities [E10], and policy composition capabilities let firewalls merge policies at enforcement time so consistent policies are applied to different classes of users (on-premises, private and public clouds) [E11].

8. **Web application protection**: Web application firewalls with advanced URL filtering detect traffic from malicious URLs and prevent web-based threats and attacks using real-time data analyzed by machine learning [E12]; they inspect threat vectors such as SQL injection, OS command injections, and cross-site scripting attacks, prevent inbound attacks, and are used in CDNs and to prevent DDoS attacks [E13].

In summary, enhanced firewall capabilities improve network security by moving from simple perimeter packet blocking to deep inspection, enterprise-wide threat detection and correlation, granular access control, internal segmentation against lateral movement, and protection of web applications against injection, scripting, and denial-of-service attacks.
</answer>