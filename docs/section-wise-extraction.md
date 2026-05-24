# SECTION-WISE Extraction Notes

Source file: `C:\Users\ahmad\Downloads\SECTION-WISE.zip`

The archive contains 12 section-wise DOCX timetables:

- CS: 2nd, 3rd, 4th, and 5th semester plans
- AI: 2nd, 3rd, 4th, and 5th semester plans
- CYS: 2nd and 4th semester plans
- SE: 2nd and 4th semester plans

## Real Slot Pattern

The documents use this daily timing model:

- 0900-0950
- 1000-1050
- 1100-1150
- 1200-1250
- Break 1250-1320
- 1320-1410
- 1420-1510
- 1515-1605
- 1610-1700

ReSched AI now uses this pattern instead of generic demo slots.

## Real Lab Pattern

Labs are usually continuous 3-contact-hour blocks. Observed lab rooms include:

- Room 117
- Room 119
- Room 120
- Room 142
- Room 143

ReSched AI now models labs as 3-period sessions and allocates them only to lab rooms.

## Real Courses Added To Seed Dataset

- CS112 Object Oriented Programming
- CS216 Data Structures
- CS216L Data Structures Lab
- CS260 Computer Networks
- CS260L Computer Networks Lab
- CS305 Software Engineering
- CS215 Information Security
- CS344 Artificial Intelligence
- CS344L Artificial Intelligence Lab
- AI233 Machine Learning
- AI321 Knowledge Representation and Reasoning
- AI324 Natural Language Programming
- AI335 Deep Learning
- AI335L Deep Learning Lab
- CS332 Design and Analysis of Algorithms
- CS325 Operating Systems
- CS325L Operating Systems Lab
- CY103 Information Assurance
- CY223 Network Security
- CY223L Network Security Lab
- SE200 Software Requirement Engineering
- SE216 Software Design and Architecture
- SE414 IoT for Software Engineering
- SE414L IoT for Software Engineering Lab
- CS226 Computer Organization and Assembly Language

## AI CCP Use

These extracted details make the CCP demo stronger because the system is no longer using random fake data. The real timetable plan informs:

- CSP variables: section-course sessions
- CSP domains: teacher, room/lab, day, and contiguous time window
- Hard constraints: teacher/room/section/repeat-student clashes, teacher expertise, availability, room capacity, lab room requirements
- Soft constraints: compactness, early release, fairness recovery, teacher workload balance, difficult course early preference, continuous labs
- Explainable AI: every slot records why the selected teacher, room, time, and repeat-student protection were valid
