Internal
========


1. Install libgit2 via brew

```brew install libgit2```


2. Install pygit2 via pip or easy_install

```sudo easy_install pygit2```
or

```sudo pip install pygit2```



How to create CSV hour bookings from GIT
=================================


The problem
-----------------

You and your co-devs and haven't booked the hours you worked because you have been lazy, so the boss is angry.

Fair and simple.

*- Sidenote: other reasons may apply*


Pre Requirements and resources
--------------------------------------------

You have a bunch of projects. And you want to assign some hours to them depending on your team's commits.
You have the yearly total of hours (capable) for each project you worked on (coming from JIRA or other ticketing systems).

The first thing that comes in mind is to use git and go straight to all the repos you need and somehow do a calculation on the hours.

Git records timestamps of the each commit, including the commiter's name and the author's name. That information is valuable if you want to back up what you have booked for your yearly timesheet.


Early limits
------------

We know the way to collect the information but the calculations seem to need a bit more thinking.
Each developer probably has worked at more than one projects for some days and that adds some complexity. You cannot go straightforward and assign e.g. 8hours to  **dev Author Nick** for **project A** because he might also have worked on project B.

On top of that you cannot just assign 4hours to Nick for project A and 4hours for project B for a day because for that day the project A might only need 2hours and project B 6hours.

From now on we will refer to developers as of authors.

**Limits/rules**:

- Each Author (Developer) cannot work more than N hours each day. For reasons of simplicity we will use 8 hours per day.
- Each Author can work on more than one project per day but the total amount of hours in sum should not exeed the above 8hours.
- Each Project can have it's own specific amout of hours required.
- According to the above an Author might need to work eg 2 hours on one project and 6 on another in one day
- The total hours for a project cannot be greater than the amount of authors multiplied by the days they worked multiplied by the hours they work N (8hours default)

The Setup
--------------

A json file with the repo settings (name, src or git) and how many hours we want to distribute for a period of time.

**Example**

We have 3 projects, 3 days and 3 authors. In 3 days, 3 authors can work 24*3 hours so the total amount of hours should be 72 hours.

We distribute in a json file the hours I need per project.

- Example:

```
{
    "ProjectA": {
        "src": "/Users/projects/projectA/",
        "total_hours": 16
    },
   "ProjectB": {
        "src": "/Users/projects/projectB/",
        "total_hours": 30
    },
    "ProjectC": {
        "src": "/Users/projects/projectC/",
        "total_hours": 8
    }
}
```


First Step - Gathering Data
------------------------------------

Let's Iterate thought all the repos, and collect all repo authors, active dates, and commits and structure them in nices trees with root entity the day. You could also use as root entity the project but I ll  use days for now.

*This can be easyly done in Python with libgit2 and pygit2 reading from the json file provided above (see provided python script).*

Example Tree:

```
       DAY                        Day            Day
     01-01-13                  02-01-13        03-01-13
  /    |   \                   /  |   \          /  |
 pA    pB    pC              pA   pB   pC       pA  pB
 |    / \    | \ \          / |   |    |       /   / | \
 S   D   N   D S N         S  D   D    N      D   S  D  N
```

Where ```pA, pB, pC, pD``` are 4 different projects from the json setup.
````S, N, D``` are 3 different authors ```Sander, Nick, Dimitri```



Second Step - Analisys and colissions calculation
------------------------------------------------------------------

We need to make sure that the limits definined above apply so we need to detect on what days the authors need to share hours between projects and how much.

We will make an absrtact here.

Let's say that each developer has a bread with him. He get's it when he enters the office and leaves a piece of it on each project that he has work equaly. So if he has worked on two projects he leaves one half on one project and another half to the other project and so on.

Considering that one bread = 1 and half = 0.5 our trees become:

```
       DAY                         Day           Day
     01-01-13                    02-01-13       03-01-13
  /     |    \                    / |  \         /  |
 pA    pB      pC               pA  pB  pC     pA   pB
 |    /  \   | \  \            / |  |   |      /   / | \
 S   D   N   D  S  N          S  D  D   N     D    S D  N
.5  .5  .5  .5  .5 .5         1 .5 .5   1    .5    1 .5 1
```

Now to do the 1st test let's sum up those breads:

```Sum = 10*0.5 + 4*1 = 9 breads```

And getting the hours simply do:

```total_hours_available = 9*8hours = 72hours``` ;-)


Now let's go a bit further and calculate the sum of available breads per project from the above tree.
The result is

```sum(project A) = 2.5 breads```


```sum(project B) = 4 breads```


```sum(project C) = 2.5 breads```


```total = 9 breads```


Third Step - Defining limits
-----------------------------------

Having knowladge on from the above distribution our limits are clearly defined:

**Total hours available**

- ```project A : 2.5 breads * 8 hours = 20 hours```
- ```project B : 4 breads * 8 hours = 32 hours```
- ```project C : 2.5 breads * 8 hours = 20 hours```

The problem is how will be distribute this amount of total hours available

Third step - Equal distriburion
---------------------------------------

We will create a setup here to distribute the above hours. We will not use the full capicity defined by the limits but a bit less. 4 hours less for project A, 2 for B and 12 for C.

This way we can try to simulate a generic model for distributing the hours instead of basing only on the limits.

Our setup has:

- ```project A : 16 hours```
- ```project B : 30 hours```
- ```project C : 8 hours```

Which is whithin the limits.

Now lets find the ratio that is corresponds accroding to the breads we have in total.
If ```project A ``` has 16 hours and 2.5 breads available then 1 bread is 6.4 hours so the ratio we can say that is ```6.4hours/bread``` for project A.

Then we have:

- ```project A : 16 hours/2.5 breads = 6.4hours/bread```
- ```project B : 30 hours/4 breads = 7.5 hours/bread```
- ```project C : 8 hours/2.5 breads =  3.2 hours/bread```


Fourth Step - Testing
----------------------------

In order to test let's distribute the previous results and do the calculations using the current setup:

```
     Day                          Day                 Day
    01-01-13                    02-01-13            03-01-13
  /   |     \                   /   |  \              /   \
 pA   pB      pC              pA   pB  pC           pA    pB
 |   / \    /  \  \          /    /  |  \          /   /  |  \
 S   D  N   D    S  N       S    D   D   N        D    S  D   N
.5  .5  .5  .5   .5 .5      1   .5   .5   1      .5    1  .5   1
3.2 3.7 3.7 1.6  1.6 1.6    6.4 3.2  3.7 3.2     3.2   7.5 3.7 7.5
```

The numbers at the end of the trees represent hours and the parent of theirs is the amount of "bread".

*3.7 = 3.75 for compactness*

Validating results
----------------------

Let's check the results

**Per project:**

- ```project A: 3.2 + 6.4 + 3.2 + 3.2 = 16 hours```
- ```project B: 3.75 + 3.75 + 3.75 + 7.5 + 3.75 + 7.5  = 30 hours```
- ```project C: 1.6 + 1.6 + 1.6+ 3.2 = 8 hours```

Sum = 16 + 30 + 8 = 54 hours

**Per author:**

- **Sander**
- - ```Day 1:  3.2 + 1.6 = 4.8 hours```
- - ```Day 2: 6.4 hours```
- - ```Day3: 7.5 hours```

- **Nick**
- - ```Day1: 3.75 + 1.6 = 5.35 hours```
- - ```Day 2: 3.2 hours```
- - ```Day 3: 7.5 hours```

- **Dimitris**
- - ```Day 1: 3.75 + 1.6 = 5.35 hours```
- - ```Day 2: 3.2 + 3.75 = 6.95 hours```
- - ```Day 3: 3.2 + 3.75 = 6.95 hours```

```Sum = 54 hours```

Tests PASS!!!


Export
--------

Easily a tree like the above can be exported to csv just by iterating thought the paths or even better using keys. Since tree joins are difined by keys ususaly in dictionary structures, then if the key is provided the access is faster or more precise.

*If for example you stored the above trees in a dictionary like ```[day][author][hours]``` then if you knew the keys of day, authoer, hours then the access would be faster than using lists or arrays.*

