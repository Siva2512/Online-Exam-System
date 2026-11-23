import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from backend.config import Config

try:
    import pymysql
    import pymysql.cursors
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False



def get_connection():
    """Connect to the configured database without silently changing databases."""
    if Config.DB_TYPE == "mysql":
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError(
                "PyMySQL is not installed. Run: pip install PyMySQL"
            )

        if not Config.DB_HOST:
            raise RuntimeError("DB_HOST is missing from .env")

        return pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            charset="utf8mb4",
            connect_timeout=10,
        ), "mysql"

    # SQLite for local development
    db_file = Path(Config.SQLITE_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

    """
    Returns a database connection based on Config.
    If MySQL is configured and reachable, connects to MySQL/RDS.
    Otherwise, falls back to SQLite for local development and offline testing.
    """
    if Config.DB_TYPE == 'mysql' and PYMYSQL_AVAILABLE and Config.DB_HOST:
        try:
            conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                charset='utf8mb4'
            )
            return conn, 'mysql'
        except Exception as e:
            print(f"[Database] Could not connect to MySQL at {Config.DB_HOST}:{Config.DB_PORT} ({e}). Falling back to SQLite.")

    # SQLite fallback
    db_file = Path(Config.SQLITE_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn, 'sqlite'


def query_db(query, args=(), one=False):
    """
    Executes a SELECT query and returns a list of dictionaries (or a single dict if one=True).
    Adapts SQL parameter placeholders (%s for MySQL, ? for SQLite).
    """
    conn, db_type = get_connection()
    try:
        cur = conn.cursor()
        if db_type == 'sqlite':
            # Translate %s to ? for SQLite
            adapted_query = query.replace('%s', '?')
            cur.execute(adapted_query, args)
            rows = cur.fetchall()
            result = [dict(row) for row in rows]
        else:
            cur.execute(query, args)
            result = cur.fetchall()
        cur.close()
        return (result[0] if result else None) if one else result
    finally:
        conn.close()


def execute_db(query, args=()):
    """
    Executes an INSERT, UPDATE, or DELETE query.
    Returns (lastrowid, rowcount).
    """
    conn, db_type = get_connection()
    try:
        cur = conn.cursor()
        if db_type == 'sqlite':
            adapted_query = query.replace('%s', '?')
            cur.execute(adapted_query, args)
            conn.commit()
            last_id = cur.lastrowid
            row_count = cur.rowcount
        else:
            cur.execute(query, args)
            last_id = cur.lastrowid
            row_count = cur.rowcount
        cur.close()
        return last_id, row_count
    finally:
        conn.close()


def init_db():
    """
    Creates necessary tables and seeds default exams and demo accounts if missing.
    """
    conn, db_type = get_connection()
    try:
        cur = conn.cursor()
        if db_type == 'sqlite':
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                registration_number TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'student',
                department TEXT DEFAULT 'Computer Science',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                duration INTEGER NOT NULL,
                total_marks INTEGER NOT NULL,
                pass_marks INTEGER NOT NULL,
                status TEXT DEFAULT 'published',
                show_answers INTEGER DEFAULT 1,
                opens_at TIMESTAMP NULL,
                closes_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option INTEGER NOT NULL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                passed INTEGER NOT NULL,
                time_taken INTEGER NOT NULL,
                answers_json TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            );
            """)
            conn.commit()
        else:
            # MySQL / AWS RDS
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                registration_number VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'student',
                department VARCHAR(150) DEFAULT 'Computer Science',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id VARCHAR(50) PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                code VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                duration INT NOT NULL,
                total_marks INT NOT NULL,
                pass_marks INT NOT NULL,
                status VARCHAR(20) DEFAULT 'published',
                show_answers BOOLEAN DEFAULT TRUE,
                opens_at TIMESTAMP NULL DEFAULT NULL,
                closes_at TIMESTAMP NULL DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                exam_id VARCHAR(50) NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option INT NOT NULL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS exam_attempts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                exam_id VARCHAR(50) NOT NULL,
                score INT NOT NULL,
                total_questions INT NOT NULL,
                percentage DECIMAL(5,2) NOT NULL,
                passed BOOLEAN NOT NULL,
                time_taken INT NOT NULL,
                answers_json TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
        cur.close()
    finally:
        conn.close()

    # Seed initial exams and questions
    seed_exams_and_questions()


def seed_exams_and_questions():
    """Seeds default demo accounts, exams, and questions if not present."""
    # 1. Demo accounts
    existing_admin = query_db("SELECT id FROM users WHERE email = %s", ('admin@college.edu',), one=True)
    if not existing_admin:
        admin_hash = generate_password_hash("Admin@123")
        execute_db(
            "INSERT INTO users (name, email, registration_number, password_hash, role, department) VALUES (%s, %s, %s, %s, %s, %s)",
            ('Dr. R. Venkatesh', 'admin@college.edu', 'ADM001', admin_hash, 'admin', 'Examination Cell')
        )

    existing_student = query_db("SELECT id FROM users WHERE email = %s", ('ananya@college.edu',), one=True)
    if not existing_student:
        student_hash = generate_password_hash("Student@123")
        execute_db(
            "INSERT INTO users (name, email, registration_number, password_hash, role, department) VALUES (%s, %s, %s, %s, %s, %s)",
            ('Ananya Krishnan', 'ananya@college.edu', '22AD014', student_hash, 'student', 'Artificial Intelligence and Data Science')
        )

    # 2. Exams
    exams_data = [
        (
            'aws-basics',
            'AWS Basics',
            'AWS-101',
            'AWS Basics Certification Practice Test',
            'Assess your understanding of cloud concepts, EC2, S3, IAM, VPC, subnets, security groups, RDS, and load balancing.',
            30,
            10,
            6,
            'published',
            1
        ),
        (
            'networking-basics',
            'Networking Basics',
            'NET-101',
            'Computer Networking Fundamentals Test',
            'Assess your understanding of OSI model, TCP/IP, IP addressing, subnetting, CIDR, DNS, DHCP, routing, switches, and troubleshooting.',
            30,
            10,
            6,
            'published',
            1
        )
    ]

    for ex in exams_data:
        existing_ex = query_db("SELECT id FROM exams WHERE id = %s", (ex[0],), one=True)
        if not existing_ex:
            execute_db(
                "INSERT INTO exams (id, category, code, title, description, duration, total_marks, pass_marks, status, show_answers) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                ex
            )

    # 3. AWS Questions
    aws_count = query_db("SELECT COUNT(*) as c FROM questions WHERE exam_id = %s", ('aws-basics',), one=True)
    if aws_count and aws_count['c'] == 0:
        aws_questions = [
            (
                'aws-basics',
                'In the AWS Shared Responsibility Model, which of the following is a responsibility of the customer when running an Amazon EC2 instance?',
                'Physical security of the data center facilities',
                'Guest operating system patching and updates',
                'Maintenance of host hardware and hypervisors',
                'Disposing of decommissioned storage disks',
                1,
                'Customers are responsible for security "in" the cloud, which includes guest OS patching, application software, and IAM configurations.'
            ),
            (
                'aws-basics',
                'What AWS compute service provides scalable virtual machines with customizable CPU, memory, and storage configurations?',
                'Amazon Elastic Compute Cloud (EC2)',
                'AWS Lambda',
                'Amazon Elastic Container Service (ECS)',
                'AWS Elastic Beanstalk',
                0,
                'Amazon EC2 provides resizable compute capacity in the form of virtual server instances.'
            ),
            (
                'aws-basics',
                'Which Amazon S3 storage class is best suited for frequently accessed, mission-critical data requiring high throughput and low latency?',
                'S3 Glacier Deep Archive',
                'S3 Standard',
                'S3 Glacier Flexible Retrieval',
                'S3 One Zone-IA',
                1,
                'S3 Standard is designed for frequently accessed data with millisecond access latency and 99.999999999% durability.'
            ),
            (
                'aws-basics',
                'Which AWS IAM entity should be attached to an Amazon EC2 instance to allow it to securely access an Amazon S3 bucket without embedding permanent credentials in application code?',
                'IAM Group',
                'IAM User access keys',
                'IAM Role',
                'Root account credentials',
                2,
                'IAM Roles supply temporary security credentials to AWS services like EC2, avoiding hardcoded secrets.'
            ),
            (
                'aws-basics',
                'What AWS service allows you to provision a logically isolated section of the AWS Cloud where you can launch resources in a virtual network that you define?',
                'Amazon CloudFront',
                'AWS Direct Connect',
                'Amazon Virtual Private Cloud (VPC)',
                'AWS Route 53',
                2,
                'Amazon VPC enables you to configure your own IP range, subnets, route tables, and network gateways.'
            ),
            (
                'aws-basics',
                'What distinguishes a public subnet from a private subnet in an Amazon VPC?',
                'A public subnet has a route table directing default internet traffic (0.0.0.0/0) to an Internet Gateway (IGW)',
                'A public subnet does not support security groups',
                'A private subnet cannot contain any database instances',
                'A public subnet only allows inbound traffic and blocks all outbound traffic',
                0,
                'A subnet is public if its route table routes outbound internet traffic to an attached Internet Gateway (IGW).'
            ),
            (
                'aws-basics',
                'Which statement correctly describes the behavior of AWS Security Groups?',
                'They operate at the subnet level and are stateless',
                'They operate at the instance/ENI level and are stateful',
                'They automatically deny return traffic for allowed incoming connections',
                'They evaluate rules strictly in numerical order from top to bottom',
                1,
                'Security Groups operate at the virtual network interface level and are stateful (return traffic is automatically allowed).'
            ),
            (
                'aws-basics',
                'When deploying a Multi-AZ Amazon RDS MySQL database, how does AWS provide high availability and automated failover?',
                'By distributing read traffic across multiple asynchronous read replicas',
                'By synchronously replicating data to a standby instance in a different Availability Zone',
                'By backing up snapshots to Amazon S3 every 5 minutes',
                'By automatically sharding tables across multiple database servers',
                1,
                'Multi-AZ RDS deployments synchronously replicate data to a standby replica in another AZ to ensure high availability and automatic failover.'
            ),
            (
                'aws-basics',
                'Which Elastic Load Balancer (ELB) type is specifically optimized for routing HTTP and HTTPS traffic at Layer 7 of the OSI model based on request paths and host headers?',
                'Network Load Balancer (NLB)',
                'Gateway Load Balancer (GWLB)',
                'Application Load Balancer (ALB)',
                'Classic Load Balancer (CLB)',
                2,
                'Application Load Balancer (ALB) operates at Layer 7 and supports advanced HTTP request routing rules.'
            ),
            (
                'aws-basics',
                'To build a fault-tolerant, highly available web tier in AWS, what combination of services should be used across multiple Availability Zones?',
                'A single large EC2 instance with an attached EBS volume',
                'An Application Load Balancer with an Auto Scaling Group spanning multiple AZs',
                'An S3 bucket mounted directly as a local hard drive',
                'A single private subnet with multiple Network Access Control Lists',
                1,
                'Combining an Application Load Balancer with an Auto Scaling Group across multiple AZs ensures traffic distribution and automated recovery.'
            )
        ]
        for q in aws_questions:
            execute_db(
                "INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                q
            )

    # 4. Networking Questions
    net_count = query_db("SELECT COUNT(*) as c FROM questions WHERE exam_id = %s", ('networking-basics',), one=True)
    if net_count and net_count['c'] == 0:
        net_questions = [
            (
                'networking-basics',
                'In the 7-layer OSI model, at which layer do protocols such as TCP and UDP operate to provide end-to-end communication services?',
                'Network Layer (Layer 3)',
                'Transport Layer (Layer 4)',
                'Data Link Layer (Layer 2)',
                'Session Layer (Layer 5)',
                1,
                'The Transport Layer (Layer 4) manages end-to-end communication, flow control, and error detection (TCP/UDP).'
            ),
            (
                'networking-basics',
                'How does a Media Access Control (MAC) address differ from an Internet Protocol (IP) address?',
                'MAC addresses are 32-bit logical addresses; IP addresses are 48-bit physical addresses',
                'MAC addresses are assigned dynamically by DHCP servers across wide area networks',
                'MAC addresses are 48-bit physical hardware identifiers burned into NICs, while IP addresses are logical network addresses',
                'MAC addresses only operate at the Application Layer of the OSI model',
                2,
                'MAC addresses are unique physical identifiers on the network card (Layer 2), while IP addresses are logical addresses assigned for Layer 3 routing.'
            ),
            (
                'networking-basics',
                'According to RFC 1918, which of the following IPv4 address ranges is reserved exclusively for private internal networks and is non-routable on the public internet?',
                '172.16.0.0 – 172.31.255.255',
                '11.0.0.0 – 11.255.255.255',
                '192.169.0.0 – 192.169.255.255',
                '224.0.0.0 – 239.255.255.255',
                0,
                'RFC 1918 private ranges include 10.0.0.0/8, 172.16.0.0/12 (172.16.0.0 - 172.31.255.255), and 192.168.0.0/16.'
            ),
            (
                'networking-basics',
                'In IPv4 CIDR notation, how many usable host IP addresses are available in a /28 subnet (mask 255.255.255.240)?',
                '16',
                '14',
                '30',
                '62',
                1,
                'A /28 subnet has 32 - 28 = 4 host bits. 2^4 = 16 total addresses minus 2 (network and broadcast) = 14 usable host IPs.'
            ),
            (
                'networking-basics',
                'What is the primary role of the Dynamic Host Configuration Protocol (DHCP) on a local network?',
                'Translating human-friendly domain names into numerical IP addresses',
                'Automatically assigning IP addresses, subnet masks, default gateways, and DNS servers to client devices',
                'Encrypting web communications using TLS certificates',
                'Routing packets between different autonomous systems across the internet',
                1,
                'DHCP automates network configuration by assigning IP parameters to clients joining the network.'
            ),
            (
                'networking-basics',
                'What security mechanism does HTTPS use to protect HTTP data in transit between a web browser and a server?',
                'Transport Layer Security (TLS / SSL) encryption and digital certificates',
                'Border Gateway Protocol (BGP) routing policies',
                'Address Resolution Protocol (ARP) spoof prevention',
                'Cyclic Redundancy Check (CRC) error detection only',
                0,
                'HTTPS uses TLS/SSL encryption and X.509 digital certificates to provide confidentiality and verify server authenticity.'
            ),
            (
                'networking-basics',
                'What is the fundamental difference in forwarding behavior between a standard Layer 2 network switch and a Layer 3 router?',
                'Switches forward frames based on MAC addresses within a LAN; routers forward packets based on IP addresses between different networks',
                'Switches operate using IP routing tables, while routers inspect only physical voltage signals',
                'Switches connect different broad geographical regions, whereas routers only connect devices within a single office room',
                'Switches block broadcast traffic by default, while routers always flood broadcasts to all ports',
                0,
                'Switches forward Layer 2 frames within the local area network using MAC address tables; routers forward Layer 3 packets between different subnets/networks.'
            ),
            (
                'networking-basics',
                'Why are Virtual Local Area Networks (VLANs) used within modern enterprise network architectures?',
                'To eliminate the need for physical Ethernet cables entirely',
                'To logically segment a single physical switch network into multiple distinct broadcast domains for security and performance',
                'To convert analog telephone signals into digital packets',
                'To replace the need for DNS lookups',
                1,
                'VLANs partition physical switches into logically separate broadcast domains, improving network segmentation and security.'
            ),
            (
                'networking-basics',
                'What is the function of the "Default Gateway" configured on a computer network interface?',
                'The IP address of the device to which packets destined for outside the local subnet are sent',
                'The external public IP assigned by the Internet Service Provider',
                'The MAC address of the DNS resolver',
                'The port number reserved for listening to incoming web server connections',
                0,
                'When sending packets to an IP address outside the local subnet, the host forwards the traffic to its configured default gateway router.'
            ),
            (
                'networking-basics',
                'Which command-line utility sends ICMP Echo Request messages to test basic IP reachability to a remote host and measure round-trip latency?',
                'netstat',
                'ping',
                'ipconfig / ifconfig',
                'nslookup',
                1,
                'The ping tool uses ICMP Echo Request and Echo Reply messages to test end-to-end IP reachability and latency.'
            )
        ]
        for q in net_questions:
            execute_db(
                "INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                q
            )
