# PPT Master 优化路线图

> 分支：`feat/text-and-pipeline-optimization`
> 状态：待开发（仅规划）

---

## 背景

当前 pipeline 存在两个可优化的瓶颈：

1. **文本溢出/覆盖**：`drawingml_utils.py` 中的 `estimate_text_width()` 使用按字符类型的粗糙启发式（CJK=1em、英文=0.55em），导致 PPTX 文本框尺寸与实际渲染偏差 15-40%，长文本经常溢出或被 PowerPoint 的 `spAutoFit` 暴力缩字。
2. **导出串行瓶颈**：LLM 生成完全部 SVG 后，`finalize_svg.py` 和 `svg_to_pptx.py` 顺序处理所有文件。对于 20-30 页 deck，后处理耗时明显。

---

## 方案一：精确文本测量与溢出修正

### 问题
- `estimate_text_width()` 无法准确反映真实字体渲染宽度
- SVG 中没有自动换行机制，全靠 LLM 手动断行
- PPTX 导出后文本溢出或字号被压缩

### 目标
- 用实际字体度量替代启发式估算
- 在导出前检测并修正溢出的文本
- 保持零额外 runtime 依赖（纯 Python）

### TODO

- [x] **1.1 调研 Python 字体度量方案**
  - Pillow `ImageFont.truetype().getlength()` 准确率优秀（±2-3%），性能 negligible（缓存后 µs 级）
  - `fonttools` / `freetype-py` 作为备选已评估，Pillow 零额外依赖且已集成，不引入备选
  - 跨平台策略：`PPT_MASTER_FONT_DIR` 环境变量 + 平台默认目录（Windows: `%WINDIR%\Fonts`, macOS: `/System/Library/Fonts`, Linux: `/usr/share/fonts`）

- [x] **1.2 构建跨平台字体解析器**
  - `_resolve_font(font_family, font_weight, font_style)` 已实现，带 `@lru_cache` 缓存
  - 字体映射表覆盖 60+ 常见字体（CJK/Latin/日文/韩文），含 bold/italic 变体
  - 回退扫描：硬编码表未命中时遍历字体目录按 stem 匹配
  - 支持 `PPT_MASTER_FONT_DIR` 自定义字体目录

- [x] **1.3 替换 `estimate_text_width()`**
  - `drawingml_utils.py` 已修改
  - 新路径：`_resolve_font` → `ImageFont.truetype(path, size)` → `getlength(text)` + 2px 安全边距
  - 旧启发式完整保留作为 fallback（字体缺失 / Pillow 未安装时自动降级）
  - `drawingml_elements.py:1030` 调用点已传递 `fonts.get('ea', '')`

- [ ] **1.4 增加文本溢出检测后处理（可选增强）**
  - 新增 `scripts/text_fit_checker.py`
  - 输入：Executor 生成完的 SVG 文件
  - 处理：遍历所有 `<text>`，用精确度量检测是否超出 slide/容器边界
  - 输出：对溢出文本自动计算断行点，插入 `<tspan x="..." dy="...">`
  - CJK 断行规则：按字符；英文断行规则：按空格/连字符
  - 处理 `letter-spacing`、`text-anchor` 等复杂属性（溢出检测时跳过或标记 warn）

- [ ] **1.5 质量检查器增强**
  - 增强 `svg_quality_checker.py:504` 的正则检查
  - 增加基于精确度量的溢出预警（不只是字符数 >100）

- [ ] **1.6 测试与验证**
  - 在 Windows / macOS / Linux 三平台测试字体加载
  - 用包含中英文混合、不同字号、bold 的 SVG 验证宽度准确性
  - 对比 SVG 预览 vs PPTX 实际渲染的文本框尺寸

### 预估工作量
- **阶段 1（1.1-1.3）**：1-2 天，投入产出比极高
- **阶段 2（1.4-1.6）**：3-4 天，可选增强

---

## 方案二：后台流式 SVG → PPTX 预转换

### 问题
- 当前流程：LLM 生成完全部 SVG → `finalize_svg.py` 顺序处理 → `svg_to_pptx.py` 顺序转换 → ZIP 组装
- 用户感知：LLM 生成完后还要等很久才能拿到 PPTX
- 技术事实：`finalize_svg.py` 和 `convert_svg_to_slide_shapes()` 都是单文件独立处理，天然可并行

### 目标
- LLM 每生成一页 SVG，后台立即预转换，缓存结果
- 当 LLM 写完最后一页时，PPTX 已"几乎就绪"，只需秒级 ZIP 组装
- 不改变 LLM 串行生成顺序（保证跨页设计一致性）

### TODO

- [x] **2.1 调研现有代码的并行化可行性**
  - `finalize_svg.py` 各步骤无跨文件依赖（每个步骤内文件完全独立）
  - `convert_svg_to_slide_shapes()` 无跨 slide 依赖（单文件纯函数）
  - `pptx_builder.py` 跨页状态已梳理：`media_cache`（去重）、`mixed_animation_offset`（累加）、`image_exts_used`（集合）— 均可在并行转换后由主线程顺序汇总

- [ ] **2.2 `finalize_svg.py` 增加单文件模式**
  - 新增 `--file <svg_path>` 参数，只处理单个 SVG
  - 或新增 `--input-dir` / `--output-dir` 参数，支持不依赖项目目录的调用
  - 保持向后兼容（无参数时仍走完整项目目录模式）

- [ ] **2.3 新增预转换缓存模块**
  - 新建 `scripts/svg_to_pptx/slide_cache.py`
  - 数据结构：
    ```python
    {
      "slide_num": int,
      "slide_xml": str,
      "media_files": dict[str, bytes],
      "rel_entries": list[dict],
      "anim_targets": list,
      "transition_cfg": dict,
      "animation_cfg": dict,
      "notes_content": str,
      "narration_audio": Path | None,
    }
    ```
  - 持久化到临时目录（`tempfile.mkdtemp(prefix="pptx_slide_cache_")`）

- [ ] **2.4 新增后台 Worker / Watcher**
  - 新建 `scripts/pptx_worker.py`（或集成到 `project_manager.py`）
  - 监听 `svg_output/` 目录的新文件事件（`watchdog` 库或轮询）
  - 检测到新 SVG 后：
    1. 调用 finalize 单文件模式 → 产出 `svg_final/<name>.svg`
    2. 调用 `convert_svg_to_slide_shapes()` → 产出 slide_cache
    3. 写入缓存目录
  - 支持幂等：同一文件多次修改时覆盖缓存

- [ ] **2.5 修改 `pptx_builder.py` 支持缓存组装**
  - 新增 `assemble_pptx_from_cache(cache_dir, output_path, ...)`
  - 从缓存目录读取所有预生成的 slide 数据
  - 执行跨页状态汇总（media_cache 去重、mixed_animation_offset 累加等）
  - 一次性 ZIP 组装
  - 复用现有的 `create_pptx_with_native_svg` 中的 ZIP 组装逻辑

- [ ] **2.6 集成到 SKILL.md workflow**
  - 在 Step 6（Executor SVG generation）和 Step 7（Post-processing）之间增加可选的 Worker 启动
  - 或者由 `project_manager.py` 在 `init` 时根据配置决定是否启用后台预转换
  - 保持默认行为不变（用户无感知切换）

- [x] **2.7 增加纯并行模式（不启用 Worker 时的 fallback）**
  - `finalize_svg.py`：4 个处理循环改为 `ThreadPoolExecutor.map()` 并行执行，添加 `-j/--workers` CLI 参数（默认 1=顺序，0=auto=min(cpu,4)）
  - `pptx_builder.py`：两阶段架构 — Phase 1 用 `ThreadPoolExecutor` 并行调用 `convert_svg_to_slide_shapes()`（native）或 `convert_svg_to_png()`（legacy）；Phase 2 主线程按 slide 顺序组装，处理跨页状态（media_cache、mixed_animation_offset 等）
  - `pptx_cli.py`：添加 `-j/--workers` 参数，透传给 `create_pptx_with_native_svg()`
  - 轻量版实现：不改变流程顺序，不改变任何输出格式，零额外依赖

- [x] **2.8 测试与验证**
  - 20 页 deck 性能基准（Windows, 4 workers）：
    - Native 模式：1.81s → 1.38s（**+31%**）
    - Legacy 模式：23.05s → 18.47s（**+25%**）
  - 功能等价验证：顺序 vs 并行产出的 PPTX 文件大小一致、内容一致
  - 异常处理验证：并行阶段异常正确 propagate 到主线程，行为与顺序模式一致

### 预估工作量
- **2.1-2.2（单文件模式）**：0.5 天
- **2.3-2.5（缓存 + 组装）**：2-3 天
- **2.6（Workflow 集成）**：0.5 天
- **2.7（纯并行 fallback）**：0.5 天
- **2.8（测试）**：1 天
- **总计**：约 4-5 天

---

## 优先级建议

| 优先级 | 方案 | 理由 |
|--------|------|------|
| **P0** | 方案一 阶段 1（1.1-1.3） | 改动最小，准确率提升最直接，解决用户最痛的文本溢出问题 |
| **P1** | 方案二 2.7（纯并行 fallback） | 改动最小，用 `ProcessPoolExecutor` 替换 `for` 循环即可，加速明显 |
| **P2** | 方案二 2.1-2.5（Worker + 缓存） | 投入中等，用户感知提升最大（秒级导出），但架构改动较多 |
| **P3** | 方案一 阶段 2（1.4-1.6） | 增强型功能，解决 LLM 偶尔断行失败的兜底场景 |
| **P4** | 方案二 2.6（Workflow 集成） | 需要配合 SKILL.md 改动，影响 AI 行为逻辑，需谨慎 |

---

## 相关代码位置

| 文件 | 作用 |
|------|------|
| `skills/ppt-master/scripts/svg_to_pptx/drawingml_utils.py:436` | `estimate_text_width()` — 粗糙启发式 |
| `skills/ppt-master/scripts/svg_to_pptx/drawingml_elements.py:988` | `convert_text()` — 文本框尺寸计算 |
| `skills/ppt-master/scripts/svg_to_pptx/pptx_builder.py:227` | `create_pptx_with_native_svg()` — PPTX 批量组装 |
| `skills/ppt-master/scripts/svg_to_pptx/drawingml_converter.py:310` | `convert_svg_to_slide_shapes()` — 单页 SVG → DrawingML |
| `skills/ppt-master/scripts/finalize_svg.py:109` | `finalize_project()` — SVG 后处理入口 |
| `skills/ppt-master/scripts/svg_quality_checker.py:494` | `_check_text_elements()` — 文本质量检查 |
| `skills/ppt-master/references/executor-base.md:146` | 串行生成规范 |
