def visualise(threads):
    with open("index.html", "w") as index:
        lines = []

        for t in threads:
            lines.append(f"<div><a href=\"dr/res/{t.post_data.num}\">{t.post_data.subject}</a></div>")

        index.writelines(lines)