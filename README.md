<!-- markdownlint-disable MD033 -->

<p align="center">
  <img src="basalt_logo.png" alt="Basalt Logo" width="900"/>
</p>


<p align="center">

  <img src="https://img.shields.io/badge/python-3.8%2B%20(recommended%203.11)-blue" alt="Python Version">

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
- **Note** — additional text containing an answer, definition, comments, or important details.

If the node is formulated as a question, the note typically contains its answer.

If the node represents a concept or statement, the note stores supplementary information that does not affect the tree structure.

Child nodes are intended to further develop the topic and logically extend the parent node.

By default, every node has only one parent, preserving a strict tree structure.

If needed, project settings can allow a limited number of parents for a single node (from 1 to 5, configurable in View Settings). This makes it possible to model situations where an effect results only from the combination of multiple causes. To preserve readability, the maximum number of parents is user-defined.

The number of child nodes is unlimited, although excessively large branches are discouraged because they make the structure harder to understand.

For working with large trees, Basalt supports:

- Zooming.

New nodes can be created directly from the node's buttons:

- **➕ Child** — add a child node;
- **🔼 Parent** — add a parent node (or select an existing node as parent);
- **❌ Delete** — delete the node (with options: remove only the node, keeping its children, or delete the entire branch).

To edit a node's title, double-click it or click and start typing.  
To edit a note, click on the note area — it switches to editing mode; press **Esc** or **Ctrl+Enter** to save.

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

During a learning session, a random node is selected. The user first sees the node's **title** and tries to recall its **note** and the **titles of all direct children**. Then they click **Show Answer** (or press Space) to reveal the full information: the note and the list of child nodes (optionally with their notes). The user rates their recall using the same grading scale as Anki:

- **Again (1)**
- **Hard (2)**
- **Good (3)**
- **Easy (5)**

Based on the grade, Basalt calculates the next review interval for the node using a simplified SM-2 algorithm.

The learning mode can work in the **background**: cards pop up periodically while you do other tasks. The interval between cards is configurable (from seconds to minutes).

You can fine-tune the learning process:

- Enable/disable each tree individually.
- Choose random or sequential order of nodes within a tree.
- Adjust card appearance: font, size, window dimensions, screen position.
- Show or hide notes of child nodes immediately.

### 6. Data Storage

Internally, the knowledge base is stored in JSON format.

The following operations are supported:

- Export and import of the entire knowledge base (JSON);
- Import individual trees from JSON (via a built-in dialog with a template, support for comments and trailing commas).

> **Note:** Export to Markdown is planned but not yet implemented.

### 7. Localization

Basalt supports multiple languages out of the box:

- English
- Русский
- 中文
- Українська

You can switch the language in **View Settings** (⚙️). The interface updates immediately.

---

## Requirements

- Python 3.8 at least, Python 3.11 recommended
- PyQt5

---

## Installation

1. Clone the repository (or download the source code):

   ```bash
   git clone https://github.com/MelomanSharp/Basalt
   cd basalt
   ```

2. Install the dependencies (using a virtual environment is recommended):

   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:

   ```bash
   python main.py
   ```

---

## Usage

- **Create a tree** — click **➕ New Tree** in the toolbar.
- **Add a child node** — select an existing node and click **➕ Child** on the node.
- **Add a parent node** — select a node and click **🔼 Parent**; choose to create a new parent or select an existing node as parent.
- **Edit a title** — double-click the node title or click it and start typing.
- **Edit a note** — click the note text; the area becomes editable. Press **Esc** or **Ctrl+Enter** to save and exit.
- **Follow a link** — click a link such as `[[Tree Name]]` inside a note. If the tree does not exist, it will be created automatically and opened.
- **Customize the layout** — open **⚙️ View Settings** to change node sizes, spacing, alignment, maximum parents, and language.
- **Start learning** — click **🧠 Start Learning** to open the learning settings dialog. Configure intervals, card appearance, and per-tree options, then click **🚀 Start Learning**.
- **Stop learning** — click **⏹ Stop** in the toolbar to end the background learning mode.
- **Import a tree from JSON** — click **📥 Import Tree**, paste JSON code (comments and trailing commas are allowed), and click **Add Tree**.
- **Export / Import database** — use **💾 Save** / **📂 Open** to work with the entire knowledge base as JSON.

---

## Project Structure

```text
basalt/
├── main.py              # entry point, main window, toolbar actions
├── basalt_canvas.py     # tree rendering (QGraphicsView)
├── basalt_node.py       # data models (nodes, trees, project, layout settings, learning settings)
├── learning_mode.py     # spaced repetition engine, notification dialog, learning settings dialog
├── ui_node.py           # visual component of a single node (title, note, action buttons)
├── ui_settings.py       # view/layout settings dialog (also language selection)
├── i18n.py              # internationalization (English, Russian, Chinese, Ukrainian)
├── basalt_logo.png      # application logo (optional)
└── README.md            # this file
```

---

## Configuration

### View Settings

- Node width and height (pixels)
- Horizontal and vertical spacing between nodes
- Text alignment inside nodes (left, center, right)
- Maximum parents per node (1–5)
- Interface language

### Learning Settings

- Interval between cards (minutes/seconds)
- Shuffle order of trees
- Card window: font, font size, window size, screen position
- Show child node notes immediately
- Per-tree settings: enable/disable, order mode (random/sequential)

All settings are saved as part of the project (or globally for language).

---

## License

This project is distributed under the **MIT License**.

You are free to use, modify, and distribute the code provided that the original copyright notice is retained.

See the [LICENSE](LICENSE) file for the full license text (if included in the repository).

---

## Contributing

If you find a bug, have an idea for an improvement, or would like to add a new feature, feel free to open an **Issue** or submit a **Pull Request**.

---

**Contact:** <a href="mailto:&#112;&#097;&#118;&#101;&#108;&#115;&#111;&#108;&#111;&#100;&#117;&#107;&#104;&#105;&#110;&#064;&#112;&#114;&#111;&#100;&#111;&#110;&#046;&#109;&#101;">Send Email</a>
