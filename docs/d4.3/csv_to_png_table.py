import pandas as pd
import matplotlib.pyplot as plt
import os
import textwrap

def wrap_text(df, width=25):
    """Wrap text in all cells of the DataFrame."""
    return df.applymap(lambda x: "\n".join(textwrap.wrap(str(x), width)))

def render_csv_to_png(csv_path):
    df = pd.read_csv(csv_path)
    df = wrap_text(df, width=25)

    n_rows, n_cols = df.shape
    cell_height = 0.6
    cell_width = 2.0  # Narrower columns with wrapping

    fig_width = max(n_cols * cell_width, 10)
    fig_height = max(n_rows * cell_height + 1, 3)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=150)
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        colWidths=[1.0 / n_cols] * n_cols,
        loc='center',
        cellLoc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)

    for (row, col), cell in table.get_celld().items():
        cell.set_text_props(ha="center", va="center", wrap=True)
        cell.PAD = 0.05
        if row == 0:
            cell.set_facecolor("#d3d3d3")

    plt.tight_layout()
    output_path = os.path.splitext(csv_path)[0] + ".png"
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    print(f"✅ Rendered: {os.path.basename(csv_path)} → {os.path.basename(output_path)}")
