# KolamNet-Genetic-Algorithm-for-Generative-Kolam-Pattern-Recreation
# KolamNet — Genetic Algorithm for Generative Kolam Pattern Recreation

**Course:** Optimization Techniques
**Status:** 🟡 Planning
**Team Level:** Beginners

---

## 1. What Are We Building?

We want to create a program that uses a **Genetic Algorithm (GA)** to recreate a given Kolam pattern.

The basic idea:

```text
Target Kolam
     ↓
Convert Kolam into a representation
     ↓
Generate random candidate patterns
     ↓
Compare candidates with target
     ↓
Genetic Algorithm improves them
     ↓
Best generated Kolam
```

Our main academic goal is to demonstrate how a **Genetic Algorithm can solve a pattern-recreation optimization problem**.

---

## 2. What We Need to Learn

We don't know all the required technologies yet, so we will learn them as we build.

### Required

* **Python** — basic programming
* **NumPy** — working with arrays/data
* **Matplotlib** — displaying patterns and graphs
* **Basic image processing** — if required by our chosen approach
* **Genetic Algorithm** — our main optimization technique
* **Git & GitHub** — team collaboration

We will **not learn everything at once**. We learn only what is needed for the current stage.

---

# 3. Project Roadmap

Follow these stages in order.

### 🟢 Stage 1 — Understand the Problem

**Learn/research:**

* What is a Kolam?
* How is a Kolam constructed?
* What characteristics should our generated Kolam have?

**Output:**

A short document explaining our understanding of Kolam.

---

### 🟢 Stage 2 — Formulate the Optimization Problem

Decide:

* **Decision variables** — what will GA change?
* **Search space** — what values can they take?
* **Objective function** — how do we measure similarity?
* **Constraints** — what rules must a generated Kolam follow?

**Output:**

A clear mathematical definition of our optimization problem.

---

### 🟡 Stage 3 — Decide the Representation

A computer needs a numerical representation of a Kolam.

We will compare approaches such as:

* Pixels
* Dots and connections
* Geometric parameters

Then choose **one practical representation**.

**Output:**

```text
Kolam → Data/Chromosome → Generated Kolam
```

---

### 🟡 Stage 4 — Build a Basic Kolam Generator

Before using GA, prove that our representation works.

Goal:

```text
Chromosome
     ↓
Kolam Generator
     ↓
Kolam Image
```

We should be able to generate different patterns by changing the chromosome.

---

### 🟠 Stage 5 — Build the Fitness Function

Teach the computer how to determine:

> "How similar is this generated Kolam to the target?"

```text
Target Kolam
      +
Generated Kolam
      ↓
Similarity / Error
```

This becomes our **fitness/objective measurement**.

---

### 🔴 Stage 6 — Implement Genetic Algorithm

Learn and implement:

```text
Population
    ↓
Fitness
    ↓
Selection
    ↓
Crossover
    ↓
Mutation
    ↓
New Population
    ↓
Repeat
```

First understand these concepts with a **simple example**, then apply them to Kolam.

---

### 🔵 Stage 7 — Combine Everything

Connect:

```text
Kolam Representation
        +
Kolam Generator
        +
Fitness Function
        +
Genetic Algorithm
        ↓
Final Kolam
```

---

### 🟣 Stage 8 — Experiment & Analyze

Test different GA parameters such as:

* Population size
* Mutation rate
* Crossover rate
* Number of generations

Record:

* Best fitness/error
* Number of generations
* Execution time
* Final pattern

Create graphs and compare the results.

---

# 4. Project Structure

Start simple:

```text
KolamNet/
│
├── README.md
├── requirements.txt
├── main.py
│
├── data/
│   └── input/
│
├── src/
│
├── results/
│
└── docs/
```

We will add more files when we actually need them.

---

# 5. Team Work

Because everyone is a beginner, responsibilities are divided by **learning + implementation**, not just coding.

| Area             | Responsibility                                |
| ---------------- | --------------------------------------------- |
| Kolam Research   | Understand Kolam and collect examples         |
| Representation   | Decide how Kolam becomes data/chromosome      |
| Python/Generator | Learn Python and build pattern generation     |
| GA/Fitness       | Learn GA and develop optimization components  |
| Everyone         | Testing, documentation, report & presentation |

Responsibilities can change as the project progresses.

**Everyone should understand the complete project, not only their assigned part.**

---

# 6. GitHub Workflow

We will use:

```text
main
  ↑
Pull Request
  ↑
Feature Branch
  ↑
Individual Work
```

Basic workflow:

```bash
git pull
git checkout -b feature-name
# make changes
git add .
git commit -m "Describe the change"
git push
```

Then create a **Pull Request** and review it before merging.

---

# 7. Current Task

### 🚨 We are currently at Stage 1.

**Do not start coding the Genetic Algorithm yet.**

First:

* [ ] Install Python
* [ ] Install VS Code
* [ ] Set up Git/GitHub
* [ ] Learn basic Python
* [ ] Research Kolam
* [ ] Collect 3–5 suitable Kolam examples
* [ ] Discuss how a Kolam could be represented as data

### Our next decision:

> **How should we represent a Kolam so that a Genetic Algorithm can modify it and generate a new pattern?**

Once this is decided, we move to Stage 2.

---

## Project Rule

> **Don't try to build the entire project at once.**

We will follow:

```text
Learn → Build → Test → Understand → Move to next stage
```

**One stage at a time.**
