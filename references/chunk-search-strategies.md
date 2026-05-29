# Chunk-Based Search Strategies for Book Analysis

在分析大书（50万字+ / 478页+）时，单次全文读取不可行。必须将全文分割为多个 50k 字符的 chunk 文件，通过 grep/read_file 组合实现跨 chunk 分析。

## 1. 文本分割协议

```bash
# 分割为 50000 字符每片的 chunk 文件
# 文件名格式: chunk_{start_offset}.txt
# 文件首行标注: --- CHUNK START={offset}, LINE_OFFSET={line_count_before} ---
```

## 2. 章节探测 — grep 策略

按优先级依次尝试以下 grep 模式：

| 优先级 | 模式 | grep 命令 | 适用场景 |
|--------|------|-----------|---------|
| 1 | 中文数字章 | `grep -n '第[一二三四五六七八九十百零]\+章'` | 中文书（最常用） |
| 2 | 英文章节 | `grep -in 'chapter [0-9]'` | 英文书 |
| 3 | 中文数字节 | `grep -n '第[一二三四五六七八九十百零]\+节'` | 有小节分割的书 |
| 4 | 罗马数字 | `grep -n 'Part [IVXLCDM]\+'` | 分卷书 |
| 5 | 全大写行 | `grep -n '^[A-Z ][A-Z ]\{3,\}[A-Z]$'` | 无章节标记的备选方案 |
| 6 | 4+换行符 | 按 `\n\n\n\n` 粗略分节作为终极回退 |

**诊断技巧**：如果所有模式命中数都 <3：
- 检查书是否为分册装订（Part 1, Part 2）
- 检查章节标题是否在图片中（扫描版 → 转用 ocr-and-documents）
- 手工打开全书前几行查看格式

## 3. 案例发现 — grep in-context

在全书所有 chunk 文件中搜索含案例的关键词附近内容：

```bash
# 找到所有"比如"及其上下文（±2行）
grep -A2 -B2 '比如' chunks/chunk_*.txt

# 找到所有"例如"及其上下文  
grep -A2 -B2 '例如' chunks/chunk_*.txt

# 找到所有"举例来"及其上下文
grep -A2 -B2 '举例来' chunks/chunk_*.txt

# 找到所有"案例"相关内容
grep -A2 -B2 '案例' chunks/chunk_*.txt
```

## 4. 结论定位 — grep signal words

```bash
# 搜索"因此"、"由此可见"、"总的来说"等结论标志词
grep -A2 '因此' chunks/chunk_*.txt
grep -A2 '由此可见' chunks/chunk_*.txt
grep -A2 '总的来说' chunks/chunk_*.txt
grep -A2 '总之' chunks/chunk_*.txt
grep -A2 '所以' chunks/chunk_*.txt
```

## 5. 作者引用查找

```bash
grep -A1 '正如' chunks/chunk_*.txt
grep -A1 '参见' chunks/chunk_*.txt
```

## 6. 精读定位 — 按偏移量读取

找到内容在 chunk 文件中的位置后，使用 `read_file` 精读：

```python
# 假设章节标题在 chunk_X.txt 的第42行
# 从行42开始读60行获取该章开头
read_file('chunk_X.txt', offset=42, limit=60)

# 假设案例在 chunk_Y.txt 的第120行附近
# 从行118开始读15行获取案例完整上下文
read_file('chunk_Y.txt', offset=118, limit=15)
```

## 7. 逐章内容评估协议

对每个检测到的章节，评估其内容范围（跨几个 chunk）后再决定读取策略：

```python
chapter_estimate = {
    'title': '第3章 文件',
    'start_chunk': 'chunk_70000.txt',
    'start_line': 3,
    'end_chunk': 'chunk_110000.txt',
    'estimated_chars': 40000,  # 从start到end_chunk开头
    'strategy': 'read_start'   # 'read_start' | 'full_read' | 'skip_if_pure_refs'
}
```

判定标准：
- **章节 < 5000 chars**：完整读取，做四段分析
- **章节 5000-20000 chars**：读开头150行（论点），然后grep搜索案例+结论
- **章节 > 20000 chars**：只读开头100行获取论点，grep搜索案例+结论，标记为"长章节-仅提取精华"
- **标题含"注释"/"参考文献"/"索引"/"附录"**：标记为 refs 章节，只做简要记录

## 8. 已验证的真实场景数据

以下数据来自《智人之上》（赫拉利，478页，50万字中文PDF）的实际执行经验：

| 指标 | 实测值 |
|------|--------|
| 总文本长度 | ~501,000 chars |
| chunk 数量 | 10 个（每片 50k char） |
| 章节总数 | 11 章 + 序言 + 结语/致谢 |
| 序言位置 | chunk_0，行10 |
| 第一章位置 | chunk_40000，行35 |
| 平均每章覆盖 | 1-2 个 chunk |
| 最长章节 | 第5章（~2.5个chunk） |
| 参考部分 | chunk_450000+，最后3个chunk |
| grep "比如"命中数 | 100+ 条结果 |
| grep "例如"命中数 | 50+ 条结果 |
| grep "因此"命中数 | 40+ 条结果 |
