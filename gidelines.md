Submission Guidelines

Deadline – 05th of March 2026

Word count – 5000 - 7000 words excluding references

Submission Mode – DLE submission as a PDF document

Submission Instructions – Rename the PDF file with your PU Index number as follow,  

Ex :- 1234567_Interim.pdf  
Cover page – Use the provided cover page for the interim report
 
The following chapters are mandatory, but you may extend the structure based on your project
 
• Table of Contents
• List of Figures and Tables (if applicable)
 
 
Chapter 01 Introduction

1.1 Introduction

1.2 Problem Definition

1.3 Project Objectives

Chapter 02 System Analysis

2.1 Facts Gathering Techniques

2.2 Existing System

2.3 Drawbacks of the existing system

Chapter 03 Requirements Specification

3.1 Functional Requirements

3.2 Non-Functional Requirements

3.3 Hardware / Software Requirements

3.4 Networking Requirements (Optional)
 
 
Chapter 04 Feasibility Study

4.1 Operational Feasibility

4.2 Economical Feasibility

4.3 Technical Feasibility

Chapter 05 System Architecture

5.1 Use case diagram

5.2 Class Diagram of Proposed System

5.3 ER Diagram

5.4 High-level Architectural Diagram

5.5 Networking Diagram (Optional)

Chapter 06 Development Tools and Technologies

6.1 Development Methodology

6.2 Programming Languages and Tools

6.3 Third-Party Components and Libraries

6.4 Algorithms

Chapter 07 Implementation Progress 

 7.1 Development Environment Setup
 7.2 Implemented Features
 7.3 Screenshots / Code Snippets (where appropriate)
 7.4 Challenges Encountered and Solutions
 7.5 Current System Limitations
Chapter 08 Discussion [Max of 1 Page]

Summary of the Report

What has changed from the Proposal

Future Plans / Upcoming Work
 
References
 
Appendixes if applicable

 

 

 

1. What is an Interim Report?

An Interim Report is not a final report.

Think of it as:

A formal academic checkpoint that proves your project is feasible, well-planned, and already in progress.

In simple terms

• Proposal → What you plan to do
• Interim Report → What you have done so far, what has changed, and what you will do next
• Final Report → What you fully completed
Why lecturers care about the Interim Report

It answers these questions:

• Do you clearly understand the problem?
• Have you done proper system analysis?
• Are your requirements realistic?
• Is your architecture technically sound?
• Have you started implementation?
• Can you reflect critically on progress and limitations?
This is why the interim report is long (5000–7000 words) and structured like a serious academic document.

 

 

 

 

 

 

2. Overall Structure – How to Think About It

Each chapter answers a specific academic question:

Chapter

Question it answers

Introduction

What is the problem and why does it matter?

System Analysis

How does the current world handle this problem?

Requirements

What exactly must your system do?

Feasibility Study

Is this project realistic?

Architecture

How will the system be designed?

Tools & Technologies

Why did you choose these technologies?

Implementation Progress

What have you already built?

Discussion

What changed, what did you learn, what’s next?

 

Chapter 01 – Introduction

1.1 Introduction

Purpose:
Provide context, not technical details.

What to include

• Background of the domain
• Why this problem is important
• Industry / academic relevance
Example (Student Management System):

With the rapid digitalisation of educational institutions, manual student record management has become inefficient, error-prone, and difficult to scale. Many small and medium-scale institutions still rely on spreadsheet-based or paper-based systems, resulting in data redundancy and limited accessibility.

 

1.2 Problem Definition

Purpose:
Clearly state the exact problem, not the solution.

 

Good problem definitions are:

• Specific
• Measurable
• Realistic
 
Bad:

Managing students is hard.

Good Example:

The current manual student record management process lacks centralised data storage, role-based access control, and real-time reporting capabilities, leading to data inconsistencies and delayed decision-making.

 

1.3 Project Objectives

Purpose:
State what your system will achieve.

Use bullet points, starting with action verbs.

Example:

• To design and implement a web-based student management system
• To enable role-based access for administrators, lecturers, and students
• To provide real-time academic performance analytics
 

Chapter 02 – System Analysis

2.1 Fact Gathering Techniques

Purpose:
Show that you did proper research, not assumptions.

Typical techniques

• Interviews
• Questionnaires
• Observations
• Document analysis
 
Example:

Interviews were conducted with administrative staff and lecturers to understand current data handling practices and pain points in academic record management.

 

2.2 Existing System

Purpose:
Describe how the problem is currently handled.

Example:

The existing system relies on Excel spreadsheets maintained independently by each department, resulting in duplicated records and inconsistent data updates.

 

2.3 Drawbacks of the Existing System

Purpose:
Justify why a new system is needed.

Example:

• High risk of data loss
• No centralized access
• Manual report generation
• Poor scalability
 

Chapter 03 – Requirements Specification

3.1 Functional Requirements

What the system MUST do

Example:

• The system shall allow administrators to add, update, and delete student records.
• The system shall allow lecturers to upload marks.
 

3.2 Non-Functional Requirements

How well the system performs

Examples:

• Security: Password encryption using hashing
• Performance: Page load time < 3 seconds
• Usability: Responsive UI for mobile devices
 

3.3 Hardware / Software Requirements

Example:

• Server: Cloud-based VPS
• Database: MySQL / PostgreSQL
• Client: Web browser
 

3.4 Networking Requirements (Optional)

Only include if relevant (e.g., distributed systems, IoT).

 

Chapter 04 – Feasibility Study

This chapter proves your project is realistic.

4.1 Operational Feasibility

Will users actually use this system?

Example:

The system is designed with a familiar web-based interface, reducing the learning curve for administrative staff.

Is the staff trained to use a digital devices?

 

4.2 Economical Feasibility

Is it affordable?

Example:

The use of open-source technologies such as React and PostgreSQL significantly reduces development and deployment costs.

 

4.3 Technical Feasibility

Do you have the skills and resources?

Example:

The development team has prior experience in full-stack web development, making the proposed system technically feasible.

Does the team have the skills (Java/Python) to build this?

 

 

 

 

Chapter 05 – System Architecture

This chapter is diagram-heavy.

5.1 Use Case Diagram

Shows who can do what.

Actors:

• Admin
• Lecturer
• Student
 

5.2 Class Diagram

Shows object-oriented design. Shows your code structure (Classes, Attributes, Methods).

Example classes:

• Student
• Course
• Enrollment
 
5.3 ER Diagram

Shows database design.

Entities:

• Student
• Course
• Marks
 

5.4 High-Level Architecture Diagram

A big-picture view showing how the Frontend (App) talks to the Backend (Server) and Database.

Shows:

• Frontend
• Backend
• Database
• APIs
5.5 Networking Diagram (Optional)

 

Chapter 06 – Development Tools and Technologies

6.1 Development Methodology

How are you managing the work? usually Agile/Scrum (Sprints) or Waterfall.

Example:

Agile methodology was adopted to allow iterative development and continuous feedback.

 

6.2 Programming Languages and Tools

Briefly explain why you chose them.

Example:

• Frontend: React
• Backend: Node.js
• Database: PostgreSQL
"We chose React Native for cross-platform support."

6.3 Third-Party Libraries

Are you using Google Maps API? Stripe for payments?

Example:

• JWT for authentication
• Chart.js for analytics
 

6.4 Algorithms

Only include important logic, not trivial loops.

Example:

• GPA calculation algorithm
• Recommendation logic
"The Shortest Path algorithm for delivery routing" or "Hashing algorithms for passwords."

 

 

 

 

Chapter 07 – Implementation Progress (VERY IMPORTANT)

This proves real work has started.

This is the most critical difference between a proposal and an Interim Report. You must show you have started coding.

7.1 Environment Setup

Explain:

• IDE
• Version control
• Deployment environment
 

7.2 Implemented Features

List what works right now.

Example:

• User authentication module completed
• Student CRUD operations implemented
"Login and Menu View are completed."

 

7.3 Screenshots / Code Snippets

Include actual screenshots of your app running. Paste small, key snippets of code (not whole files!)

Show:

• Login page
• Dashboard
• Database tables
 

7.4 Challenges & Solutions

Critical thinking section. Be honest.

Example:

We struggled with the database connection, but fixed it by updating the connection string.

API response latency was addressed by implementing server-side caching.

 

 

7.5 Current System Limitations

Be honest.

Example:

• Mobile optimization not fully completed
• Reporting module partially implemented
 

Chapter 08 – Discussion (Max 1 Page)

What to include

1. Summary of the report
2. Changes from the proposal
3. Future plans
Example:

Compared to the initial proposal, the system scope was refined to prioritise core academic functionalities. Future work includes integrating predictive analytics for student performance.

We originally planned a delivery feature but removed it to focus on pickup.

 

 

• References: Cite all books, websites, and papers used.
• Appendices: (Optional) Extra charts, survey raw data, or long code listings
 

Final Advice

• Write formally, but clearly
• Avoid storytelling
• Every claim should sound justified
• Diagrams must be clean and readable