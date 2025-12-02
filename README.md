# PAAWS Annotation Software

A PyQt6-based video annotation tool for labeling video content with temporal annotations. Designed for physical activity and posture analysis with hierarchical category selection.

## Features

- **Dual Video Preview**: Main video player with synchronized preview window showing content ahead
- **Dual Timeline System**: Full timeline overview with detailed zoom view
- **Temporal Annotations**: Create, edit, merge, split, and delete time-based labels
- **Category-Based Labeling**: Hierarchical categories including Posture, High Level Behavior, PA Type, Behavioral Parameters, and Experimental Situation
- **Smart Label Validation**: Automatic detection of incompatible label combinations based on configurable mappings
- **Autosave**: Automatic periodic saving with video hash validation to detect file changes
- **Keyboard Shortcuts**: Comprehensive keyboard controls for efficient labeling workflow
- **Export**: Export annotations as JSON and CSV files in a ZIP archive

## Installation

### Requirements

- Python 3.11+
- PyQt6
- See `requirements.txt` for full list of dependencies

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd QtVideo

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### Basic Workflow

1. **Open Video**: Click "Open Video" or use the gear menu → "New Video"
2. **Create Annotation**: Press `A` to start labeling at current position, press `A` again to finish
3. **Edit Labels**: Press `G` to open the category selection dialog
4. **Navigate**: Use arrow keys to skip through video, or Shift+Arrow to jump between labels
5. **Export**: Use gear menu → "Export Labels" to save annotations

### Keyboard Shortcuts

#### Video Controls
- `Spacebar` - Play/Pause
- `←/→` - Skip 10s backward/forward
- `↑/↓` - Increase/decrease playback speed
- `R` - Reset speed to 1.0x
- `Shift+↑/↓` - Adjust preview skip offset

#### Annotation Controls
- `A` - Start/Stop labeling
- `G` - Open label dialog
- `Z` - Cancel current labeling
- `S` - Delete current label
- `P` - Split label at current position

#### Navigation
- `Shift+←/→` - Jump to previous/next label boundary
- `N` - Merge with previous label
- `M` - Merge with next label

#### Dialog Controls
- `1-5` - Quick access to category dropdowns in label dialog

## Configuration

### Categories
Edit `data/categories/categories.csv` to customize available label options for each category.

### Label Mappings
Edit `data/mapping/mapping.json` to define valid combinations between categories (e.g., which postures are compatible with which PA types).

## Building

The project includes GitHub Actions workflows for building standalone executables:

- **Windows**: Creates `PAAWS-Annotation-Software.exe`
- **macOS**: Creates `PAAWS-Annotation-Software.dmg`
- **Linux**: Creates `PAAWS-Annotation-Software` binary

To build manually with PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Build (example for Windows)
pyinstaller --name "PAAWS-Annotation-Software" --windowed --onefile \
  --add-data "src/VideoPlayer.qml;src" \
  --add-data "data;data" \
  main.py
```

## Testing

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_video_player.py
```

## Citation

If you use this software in your research, please cite:

Tran, H., Potter, V., Mazzucchelli, U., John, D., Intille, S. (2026). Towards Practical, Best Practice Video Annotation to Support Human Activity Recognition. In: Tonkin, E.L., Tourte, G.J.L., Yordanova, K. (eds) Annotation of Real-World Data for Artificial Intelligence Systems. ARDUOUS 2025. Communications in Computer and Information Science, vol 2706. Springer, Cham. https://doi.org/10.1007/978-3-032-09117-8_6

We also provide our citation as a bibtex:

```bibtex
@InProceedings{tran2026_toward-better-annotations,
author="Tran, Hoan
and Potter, Veronika
and Mazzucchelli, Umberto
and John, Dinesh
and Intille, Stephen",
editor="Tonkin, Emma L.
and Tourte, Gregory J. L.
and Yordanova, Kristina",
title="Towards Practical, Best Practice Video Annotation to Support Human Activity Recognition",
booktitle="Annotation of Real-World Data for Artificial Intelligence Systems",
year="2026",
publisher="Springer Nature Switzerland",
address="Cham",
pages="94--118",
abstract="Researchers need ground-truth activity annotations to train and evaluate wearable-sensor-based activity recognition models. Oftentimes, researchers establish ground truth by annotating the video recorded while someone engages in activity wearing sensors. The ``gold-standard'' video annotation practice requires two trained annotators independently annotating the same footage with a third domain expert resolving disagreements. Such annotation is laborious, and so widely-used datasets have often been annotated using only a single annotator per video. Because the research community is moving towards collecting data of more complex behaviors from free-living people 24/7 and annotating more granular, fleeting activities, the annotation task grows even more challenging; the single-annotator approach may yield inaccuracies. We investigated a ``silver-standard'' approach: rather than using two independent annotation passes, a second annotator revises the work of the first annotator. The proposed approach reduced the total annotation time by 33{\%} compared to the gold-standard approach, with near-equivalent annotation quality. The silver-standard label was in higher agreement with the gold-standard label than the single-annotator label, with Cohen's {\$}{\$}{\backslash}kappa {\$}{\$}$\kappa$of 0.77 and 0.68 respectively on a 16.4 h video. The silver-standard labels also had higher inter-rater reliability than the single-annotator labels, with the respective mean Cohen's {\$}{\$}{\backslash}kappa {\$}{\$}$\kappa$across six videos (92 h of total footage) of 0.79 and 0.68.",
isbn="978-3-032-09117-8"
}
```
