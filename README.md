<!-- markdownlint-disable MD033 -->
````md
<!-- markdownlint-disable MD033 -->

<p align="center">

  <img src="https://img.shields.io/badge/Python-3.6%2B-blue.svg" alt="Python Version">

  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">

  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform">

</p>

# Basalt

**Basalt** is a Windows application for creating structured knowledge bases in the form of trees and studying them using spaced repetition.

The project is conceptually inspired by Obsidian and Anki, combining the strengths of both approaches while introducing its own model for organizing knowledge.

---

## Features

### 1. Knowledge Representation

Unlike Obsidian, where the primary unit of information is a Markdown file, every note in Basalt is an independent tree with an unlimited number of nodes. These trees are viewed directly as interactive graphical structures rather than plain text documents.

Each tree has an explicit top-down hierarchy, progressing from general concepts to more specific ones through parent-child relationships. This makes it possible not only to store information but also to preserve logical and causal connections, making it easier to reconstruct knowledge by understanding its structure.

Almost any fact can naturally lead to the question **"Why?"**, allowing the creation of a child node that explains or refines that fact. This makes Basalt especially suitable for building knowledge bases in a **question–answer** format as well as for deeply decomposing complex topics.

The application encourages storing knowledge as a large number of small interconnected nodes instead of long monolithic notes.

### 2. Spatial Memory

One of Basalt's core ideas is the **static positioning of nodes**.

Unlike Obsidian, where the graph is automatically rearranged whenever its structure changes, existing nodes in Basalt never move when new ones are added. This allows users to leverage spatial memory, remembering not only the information itself but also its physical location within the tree.

The only automatic layout adjustment is the redistribution of available horizontal space between neighboring nodes when necessary.

### 3. Node Structure

Each node consists of two parts:

- **Title** — the main concept, question, or statement.
- **Description** — additional text containing an answer, definition, comments, or important details.

If the node is formulated as a question, the description typically contains its answer.

If the node represents a concept or statement, the description stores supplementary information that does not affect the tree structure.

Child nodes are intended to further develop the topic and logically extend the parent node.

By default, every node has only one parent, preserving a strict tree structure.

If needed, project settings can allow a limited number of parents for a single node. This makes it possible to model situations where an effect results only from the combination of multiple causes. To preserve readability, the maximum number of parents is configurable.

The number of child nodes is unlimited, although excessively large branches are discouraged because they make the structure harder to understand.

For working with large trees, Basalt supports:

- Zooming;
- Collapsing and expanding subtrees.

New nodes can be created directly from the interface:

- Bottom — add or remove a child node;
- Top — add a new parent node;
- Right — create or remove a description.

### 4. Links Between Trees

Like Obsidian, separate trees can be connected using links.

The familiar syntax is supported:

```text
[[Tree Name]]
```

or

```text
[[Tree Name|Displayed Text]]
```

Each tree has its own unique name, and navigation through links is instantaneous.

This approach makes it possible to split very large topics into multiple logically independent trees while preserving seamless navigation between them.

Basalt encourages creating many small, specialized trees instead of one enormous one.

### 5. Learning Mode

Basalt adopts Anki's spaced repetition system.

During a learning session, a random node is selected. The user first recalls the node's description and then attempts to recall all of its immediate child nodes. Recursive reproduction of the entire subtree is **not** required—only the direct children of the selected node are tested.

A **reverse learning mode** is also available, where the description is shown first and the user must recall the corresponding question or title.

The same mechanics apply recursively as new nodes are selected for review.

After each review, the user rates how well they remembered the material using the same grading scale as Anki. Basalt then calculates the intervals before future reviews based on these ratings.

### 6. Data Storage

Internally, the knowledge base is stored in JSON format.

The following operations are supported:

- Export and import of the entire knowledge base;
- Export and import of individual trees;
- Direct insertion of trees through the application interface.

For compatibility with other systems, trees can also be exported as Markdown documents, allowing the accumulated knowledge base to be used in Obsidian and other Markdown editors without manual conversion.

---

## Requirements

- Python 3.6 or later
- PyQt5

---

## Installation

1. Clone the repository (or download the source code):

   ```bash
   git clone https://github.com/yourusername/basalt.git
   cd basalt
   ```

2. Install the dependencies (using a virtual environment is recommended):

   ```bash
   pip install PyQt5
   ```

   (If a `requirements.txt` file is available, use `pip install -r requirements.txt`.)

3. Launch the application:

   ```bash
   python main.py
   ```

---

## Usage

- **Create a tree** — click **➕ New Tree** in the toolbar.
- **Add a child node** — select an existing node and click **➕ Child Node**.
- **Add a parent node** — select a node and click **🔼 Parent Node**.
- **Edit a title** — double-click the node title or click it and start typing.
- **Edit a description** — click the **✏️** button in the upper-right corner of the node, enter the text, and save it (the button changes to **💾**).
- **Follow a link** — click a link such as `[[Tree Name]]` inside a description. The referenced tree will be created automatically if it does not already exist, and then opened.
- **Customize the layout** — open **⚙️ View Settings** to change node sizes, spacing, or alignment.
- **Learning mode** — click **🧠 Start Learning** to review nodes scheduled for spaced repetition. After answering, rate your recall quality and the review intervals will be updated automatically.
- **Export / Import** — use **💾 Export Database** and **📂 Import Database** to save or load the entire knowledge base as JSON.

---

## Project Structure

```text
basalt/
├── main.py              # entry point, main window
├── basalt_canvas.py     # tree rendering (QGraphicsView)
├── basalt_node.py       # data models (nodes, trees, project, settings, intervals)
├── learning_mode.py     # learning dialog (spaced repetition)
├── ui_node.py           # node UI component
├── ui_settings.py       # view settings dialog
└── README.md            # this file
```

---

## Configuration

The **View Settings** dialog allows you to configure:

- Node width and height (in pixels);
- Horizontal and vertical spacing between nodes;
- Text alignment inside nodes (left, center, or right).

All changes apply to the current tree and are saved as part of the project.

---

## License

This project is distributed under the **MIT License**.

You are free to use, modify, and distribute the code provided that the original copyright notice is retained.

See the [LICENSE](LICENSE) file for the full license text (if included in the repository).

---

## Contributing

If you find a bug, have an idea for an improvement, or would like to add a new feature, feel free to open an **Issue** or submit a **Pull Request**.

---

**Contact:** pavelsolodukhin@proton.me
````

