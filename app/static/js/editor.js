document.addEventListener("DOMContentLoaded", function () {
  const markdownEditor = document.getElementById("markdown_content");

  if (markdownEditor) {
    const form = markdownEditor.closest("form");

    const formAction = form.getAttribute("action");
    const isPageEditor = formAction.includes("/pages/");

    const simplemde = new SimpleMDE({
      element: markdownEditor,
      spellChecker: false,
      toolbar: [
        "bold",
        "italic",
        "heading",
        "|",
        "quote",
        "unordered-list",
        "ordered-list",
        "|",
        "link",
        {
          name: "insert-media",
          action: function (editor) {
            window.dispatchEvent(
              new CustomEvent("open-media-modal", {
                detail: { editor: editor },
              })
            );
          },
          className: "fa fa-file-image-o",
          title: "Insert Media",
        },
        "|",
        "preview",
        "side-by-side",
        "fullscreen",
        "|",
        "guide",
      ],
      placeholder: isPageEditor
        ? "Write your page in Markdown..."
        : "Write your post in Markdown...",
      status: ["autosave", "lines", "words", "cursor"],
      tabSize: 4,
      renderingConfig: {
        singleLineBreaks: false,
        codeSyntaxHighlighting: true,
      },
      previewRender: function (plainText) {
        const htmlText = simplemde.markdown(plainText);

        setTimeout(function () {
          const previewEl = simplemde.codemirror.display.wrapper.nextSibling;
          if (previewEl) {
            const codeBlocks = previewEl.querySelectorAll("pre code");
            codeBlocks.forEach((block) => {
              hljs.highlightElement(block);
            });
          }
        }, 0);

        return htmlText;
      },
    });

    simplemde.codemirror.setOption("extraKeys", {
      "Ctrl-B": function (cm) {
        simplemde.toggleBold();
      },
      "Ctrl-I": function (cm) {
        simplemde.toggleItalic();
      },
      "Ctrl-K": function (cm) {
        simplemde.drawLink();
      },
      "Ctrl-Alt-I": function (cm) {
        simplemde.drawImage();
      },
      "Ctrl-Alt-M": function (cm) {
        window.dispatchEvent(
          new CustomEvent("open-media-modal", {
            detail: { editor: { codemirror: cm } },
          })
        );
      },
      "Ctrl-Alt-P": function (cm) {
        simplemde.togglePreview();
      },
      "Ctrl-Alt-S": function (cm) {
        simplemde.toggleSideBySide();
      },
    });
  }
});
