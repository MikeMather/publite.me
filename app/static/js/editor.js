document.addEventListener("DOMContentLoaded", function () {
  const markdownEditor = document.getElementById("markdown_content");

  if (markdownEditor) {
    // Get the form that contains the markdown editor
    const form = markdownEditor.closest("form");

    // Determine if this is a post or page editor based on the form action
    const formAction = form.getAttribute("action");
    const isPageEditor = formAction.includes("/pages/");

    // Extract the ID from the form action to create a unique ID for each post/page
    let contentId = "new";
    const idMatch = formAction.match(/\/(\d+)\/edit/);
    if (idMatch && idMatch[1]) {
      contentId = idMatch[1];
    }

    const uniqueId = isPageEditor
      ? `postlite-page-editor-${contentId}`
      : `postlite-post-editor-${contentId}`;

    // Initialize SimpleMDE
    const simplemde = new SimpleMDE({
      element: markdownEditor,
      spellChecker: false,
      autosave: {
        enabled: true,
        uniqueId: uniqueId,
        delay: 1000,
      },
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
            // Dispatch custom event to open the media modal
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
        // First, convert markdown to HTML
        const htmlText = simplemde.markdown(plainText);

        // After the preview is rendered, apply syntax highlighting to code blocks
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

    // Add keyboard shortcuts for common actions
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
        // Dispatch custom event to open the media modal
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

    // Add form submit event listener to update the textarea with SimpleMDE content
    if (form) {
      form.addEventListener("submit", function () {
        // Update the original textarea with the current content from SimpleMDE
        markdownEditor.value = simplemde.value();
        // Clear the autosave data after successful submission
        // We'll use setTimeout to give the form time to submit
        setTimeout(function () {
          // Check if the form was successfully submitted (page changed)
          // If not, the autosave data will remain
          if (document.querySelector(".success")) {
            localStorage.removeItem(`smde_${uniqueId}`);
          }
        }, 500);
      });
    }

    // Check for success message and clear autosave if present
    if (document.querySelector(".success")) {
      // If there's a success message on the page, clear the autosave data
      // This handles the case when the page is reloaded after a successful submission
      localStorage.removeItem(`smde_${uniqueId}`);
    }
  }
});
