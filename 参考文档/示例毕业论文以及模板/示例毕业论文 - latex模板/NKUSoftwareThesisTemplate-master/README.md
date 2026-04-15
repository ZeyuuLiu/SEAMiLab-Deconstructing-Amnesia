# 南开大学软件学院本科毕业论文 LaTeX 模板

这是一个面向南开大学软件学院本科毕业论文的 LaTeX 模板。

本项目以 `2026年软件学院本科毕业论文格式规范.pdf` 为主要对照依据进行整理与调整，目标是与 2026 年于婷老师在群里发布的模板保持一致。

同时，本项目是在南开大学计算机学院模板项目的基础上修改而来：

- 原始项目：[NKU-thesis-template-2020](https://github.com/Tr0py/NKU-thesis-template-2020.git)

## 项目说明

- 模板入口文件：`main.tex`
- 样式文件：`NKThesis.sty`
- 规范依据文件：`2026年软件学院本科毕业论文格式规范.pdf`
- 参考文献：`nkthesis.bib`
- 默认编译输出目录：`build/`

本仓库保留了软件学院本科毕业论文常用的封面、声明、摘要、目录、正文示例、参考文献与致谢等部分，并根据软件学院要求对版式、字号、颜色和示例内容做了适配。

## 编译方式

推荐使用 XeLaTeX，通过 `latexmk` 编译：

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

编译完成后，所有中间文件和最终 PDF 都会输出到 `build/` 目录，最终文件为：

```text
build/main.pdf
```

本项目当前不依赖 `Makefile`，直接使用 `latexmk` 或 VS Code 的 LaTeX Workshop 即可完成编译。

## 使用建议

- 修改论文题目信息时，优先编辑 `main.tex` 中的 `\NKTsetup{...}` 部分。
- 摘要、正文示例、参考文献、致谢等内容分别位于 `abstract.tex`、`manual.tex`、`references.tex`、`acknowledgements.tex`。
- 如果使用 VS Code，仓库中的 `.vscode/settings.json` 已经配置好默认输出到 `build/`。

## 说明

本项目的目标是为南开大学软件学院本科毕业论文提供一份更贴近学院实际要求的 LaTeX 模板；如后续学院格式要求发生变化，应以最新正式通知或模板为准。
