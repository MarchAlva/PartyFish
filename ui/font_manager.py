# 字体大小设置
font_size = 100  # 默认字体大小

input_entries = []  # 保存所有输入框引用，用于后续字体更新
combo_boxes = []  # 保存所有组合框引用，用于后续字体更新
fish_tree_ref = None  # 保存钓鱼记录Treeview引用，用于动态调整列宽


def init_font_styles(style, font_size_percent):
    """初始化所有字体样式

    Args:
        style: ttkbootstrap.Style对象
        font_size_percent: 字体大小百分比（50-200）
    """
    # 缩放因子
    scale_factor = font_size_percent / 100.0

    # 基础字体设置
    base_font = "Segoe UI"

    # 定义不同控件的字体大小
    font_sizes = {
        "Title": int(14 * scale_factor),  # 标题字体大小
        "Subtitle": int(8 * scale_factor),  # 副标题字体大小
        "Label": int(9 * scale_factor),  # 普通标签字体大小
        "Entry": int(9 * scale_factor),  # 输入框字体大小
        "Button": int(9 * scale_factor),  # 按钮字体大小
        "Treeview": int(9 * scale_factor),  # 树视图字体大小
        "Combobox": int(9 * scale_factor),  # 组合框字体大小
        "Small": int(7 * scale_factor),  # 小号字体大小
        "Stats": int(10 * scale_factor),  # 统计信息字体大小
        "StatsTotal": int(11 * scale_factor),  # 总计统计字体大小
        "LogText": int(8 * scale_factor),  # 日志文本字体大小
    }

    # 确保字体大小在合理范围内
    for key in font_sizes:
        font_sizes[key] = max(5, min(30, font_sizes[key]))

    # 更新各种控件的字体样式
    try:
        # 1. 更新标签样式
        label_font = (base_font, font_sizes["Label"])
        label_styles = ["TLabel", "TLabelframe.Label", "Status.TLabel", "Stats.TLabel"]
        for style_name in label_styles:
            style.configure(style_name, font=label_font)

        # 2. 更新输入框样式
        entry_font = (base_font, font_sizes["Entry"])
        entry_styles = ["TEntry", "Entry"]
        for style_name in entry_styles:
            style.configure(style_name, font=entry_font)

        # 3. 更新组合框样式（包括下拉列表）
        combobox_font = (base_font, font_sizes["Combobox"])
        combobox_styles = [
            "TCombobox",
            "Combobox",
            "TCombobox.Listbox",
            "Combobox.Listbox",
        ]
        for style_name in combobox_styles:
            style.configure(style_name, font=combobox_font)

        # 4. 更新复选框样式
        style.configure("TCheckbutton", font=label_font)

        # 5. 更新树视图样式
        treeview_font = (base_font, font_sizes["Treeview"])
        treeview_rowheight = int(font_sizes["Treeview"] * 2.2)
        treeview_styles = [
            ("Treeview", treeview_font, treeview_rowheight),
            ("CustomTreeview.Treeview", treeview_font, treeview_rowheight),
        ]
        for style_name, font, rowheight in treeview_styles:
            style.configure(style_name, font=font, rowheight=rowheight)
            style.configure(
                f"{style_name}.Heading", font=(base_font, font_sizes["Label"], "bold")
            )

        # 6. 更新滑块样式
        scale_styles = ["Horizontal.TScale", "Vertical.TScale"]
        for style_name in scale_styles:
            style.configure(style_name, font=label_font)

        # 7. 更新单选按钮样式
        radiobutton_styles = {
            "TRadiobutton": label_font,
            "Toolbutton.TRadiobutton": label_font,
            "InfoOutline.TRadiobutton": label_font,
            "SuccessOutline.TRadiobutton": label_font,
            "DangerOutline.TRadiobutton": label_font,
            "InfoOutline.Toolbutton.TRadiobutton": label_font,
            "SuccessOutline.Toolbutton.TRadiobutton": label_font,
            "DangerOutline.Toolbutton.TRadiobutton": label_font,
            "WarningOutline.Toolbutton.TRadiobutton": label_font,
            "SecondaryOutline.Toolbutton.TRadiobutton": label_font,
        }
        for style_name, font in radiobutton_styles.items():
            style.configure(style_name, font=font)

        # 8. 更新按钮样式
        button_font = (base_font, font_sizes["Button"])

        # 基础按钮样式
        base_button_styles = [
            "TButton",
            "Button",
            "Toolbutton",
            "Outline.TButton",
            "Toolbutton.TButton",
            "Outline.Toolbutton.TButton",
        ]
        for style_name in base_button_styles:
            style.configure(style_name, font=button_font)

        # 特定按钮样式变体
        specific_button_styles = [
            "InfoOutline.TButton",
            "SuccessOutline.TButton",
            "DangerOutline.TButton",
            "WarningOutline.TButton",
            "SecondaryOutline.TButton",
            "InfoOutline.Toolbutton.TButton",
            "SuccessOutline.Toolbutton.TButton",
            "DangerOutline.Toolbutton.TButton",
            "WarningOutline.Toolbutton.TButton",
            "SecondaryOutline.Toolbutton.TButton",
            "SuccessOutline.Toolbutton",
            "DangerOutline.Toolbutton",
            "InfoOutline.Toolbutton",
            "WarningOutline.Toolbutton",
            "SecondaryOutline.Toolbutton",
        ]
        for style_name in specific_button_styles:
            style.configure(style_name, font=button_font)

        # 颜色变体按钮样式
        color_variants = [
            "Primary",
            "Secondary",
            "Success",
            "Info",
            "Warning",
            "Danger",
            "Light",
            "Dark",
        ]
        color_button_templates = [
            f"{{}}.TButton",
            f"{{}}Outline.TButton",
            f"{{}}.Toolbutton.TButton",
            f"{{}}Outline.Toolbutton.TButton",
        ]
        bootstyle_templates = [f"{{}}-toolbutton", f"{{}}-outline-toolbutton"]

        for color in color_variants:
            # 颜色按钮样式
            for template in color_button_templates:
                style_name = template.format(color)
                style.configure(style_name, font=button_font)

            # 直接使用bootstyle名称作为样式
            for template in bootstyle_templates:
                style_name = template.format(color.lower())
                style.configure(style_name, font=button_font)

        # 9. 更新日志文本样式
        log_font = (base_font, font_sizes["LogText"])
        style.configure("LogText.TText", font=log_font)
    except Exception as e:
        print(f"Error initializing font styles: {e}")



def update_all_widget_fonts(widget, style, font_size_percent):
    """更新所有控件的字体大小

    Args:
        widget: 根控件
        style: ttkbootstrap.Style对象
        font_size_percent: 字体大小百分比（50-200）
    """
    # 初始化字体样式 - 这会更新所有控件的样式字体
    init_font_styles(style, font_size_percent)

    # 缩放因子
    scale_factor = font_size_percent / 100.0
    base_font = "Segoe UI"

    # 定义默认字体大小
    default_sizes = {
        "Label": 9,
        "Button": 9,
        "Entry": 9,
        "Combobox": 9,
        "Radiobutton": 9,
        "Checkbutton": 9,
        "Treeview": 9,
        "LogText": 8,
    }

    # 递归更新所有控件的字体
    def update_widget_font(w):
        try:
            widget_type = type(w).__name__

            # 确定默认字体大小
            if widget_type in ["Label", "TLabel", "TTKLabel"] or "Label" in widget_type:
                default_size = default_sizes["Label"]
            elif (
                widget_type in ["Button", "TButton", "TTKButton"]
                or "Button" in widget_type
            ):
                default_size = default_sizes["Button"]
            elif (
                widget_type in ["Entry", "TEntry", "TTKEntry"] or "Entry" in widget_type
            ):
                default_size = default_sizes["Entry"]
            elif (
                widget_type in ["Combobox", "TCombobox", "TTKCombobox"]
                or "Combobox" in widget_type
            ):
                default_size = default_sizes["Combobox"]
            elif (
                widget_type in ["Radiobutton", "TRadiobutton", "TTKRadiobutton"]
                or "Radiobutton" in widget_type
            ):
                default_size = default_sizes["Radiobutton"]
            elif (
                widget_type in ["Checkbutton", "TCheckbutton", "TTKCheckbutton"]
                or "Checkbutton" in widget_type
            ):
                default_size = default_sizes["Checkbutton"]
            elif (
                widget_type in ["Treeview", "TTKTreeview"] or "Treeview" in widget_type
            ):
                default_size = default_sizes["Treeview"]
            elif widget_type in ["Text", "TKText", "TTKText"] or "Text" in widget_type:
                default_size = default_sizes["LogText"]
            elif (
                widget_type in ["Frame", "TFrame", "TTKFrame"] or "Frame" in widget_type
            ):
                # 跳过框架，只处理其内部控件
                pass
            else:
                # 对于其他控件类型，尝试将其作为按钮处理，特别是ttkbootstrap按钮
                # 检查控件是否有configure方法，尝试获取其样式
                try:
                    style_name = w.cget("style")
                    if "Button" in style_name or "Toolbutton" in style_name:
                        default_size = default_sizes["Button"]
                    else:
                        return  # 跳过不支持字体的控件
                except:
                    return  # 跳过不支持字体的控件

            # 计算新字体大小
            new_size = int(default_size * scale_factor)
            new_size = max(5, min(30, new_size))

            # 构建新字体
            new_font = (base_font, new_size)

            # 特殊处理标题和粗体文本
            try:
                if widget_type == "Label" and (
                    "PartyFish" in str(w.cget("text")) or "标题" in str(w.cget("text"))
                ):
                    new_font = (base_font, int(14 * scale_factor), "bold")
                elif widget_type == "Label" and "统计" in str(w.cget("text")):
                    new_font = (base_font, int(10 * scale_factor), "bold")
                elif widget_type == "Label" and "运行日志" in str(w.cget("text")):
                    new_font = (base_font, int(10 * scale_factor), "bold")
            except:
                pass

            # 尝试直接更新控件字体，如果失败则跳过
            try:
                w.configure(font=new_font)
            except Exception as e:
                # 对于ttkbootstrap按钮，可能无法直接设置字体，需要通过样式更新
                # 这已经在init_font_styles中处理了，所以这里可以安全跳过
                pass

        except Exception as e:
            # 跳过不支持字体的控件
            pass

        # 递归处理子控件
        for child in w.winfo_children():
            update_widget_font(child)

    # 开始递归更新
    update_widget_font(widget)

    # 重新配置所有已创建的控件，应用新的样式设置
    widget.update_idletasks()
