package tv.cleanyour.app

import android.icu.text.MessagePattern
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.w3c.dom.Element
import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.fail

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], application = android.app.Application::class)
class ChineseCopyTest {
    private data class Copy(val kind: String, val variants: Map<String, String>, val translatable: Boolean)

    private fun text(element: Element): String = element.textContent.replace("\\'", "'").replace("\\\"", "\"")

    private fun read(file: File): Map<String, Copy> {
        val nodes = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(file).documentElement.childNodes
        val result = linkedMapOf<String, Copy>()
        for (i in 0 until nodes.length) {
            val element = nodes.item(i) as? Element ?: continue
            if (element.tagName !in setOf("string", "plurals")) continue
            val name = element.getAttribute("name")
            assertTrue(name !in result, "${file.path}: duplicate $name")
            val variants = if (element.tagName == "string") mapOf("" to text(element)) else {
                val items = element.getElementsByTagName("item")
                val values = linkedMapOf<String, String>()
                for (j in 0 until items.length) {
                    val item = items.item(j) as Element
                    val quantity = item.getAttribute("quantity")
                    assertTrue(quantity !in values, "${file.path}: duplicate $name/$quantity")
                    values[quantity] = text(item)
                }
                assertTrue("other" in values, "${file.path}: $name needs an other quantity")
                values
            }
            result[name] = Copy(element.tagName, variants, element.getAttribute("translatable") != "false")
        }
        return result
    }

    // Include nested arguments: Chinese may move a value out of an English plural clause.
    private fun icuArguments(text: String): Set<String> {
        val pattern = MessagePattern(text)
        return (0 until pattern.countParts()).map { pattern.getPart(it) }
            .filter { it.type == MessagePattern.Part.Type.ARG_NAME || it.type == MessagePattern.Part.Type.ARG_NUMBER }
            .map { pattern.getSubstring(it) }.toSet()
    }

    private val printf = Regex("%(?:(\\d+)\\$)?([-#+ 0,(<]*)(?:\\d+)?(?:\\.\\d+)?([tT])?([a-zA-Z%])")

    private fun printfArguments(text: String): Set<Pair<Int, String>> {
        var next = 1
        var previous = 0
        val result = linkedSetOf<Pair<Int, String>>()
        for (match in printf.findAll(text)) {
            val (explicit, flags, date, conversion) = match.destructured
            if (conversion == "%" || conversion == "n") continue
            val index = when {
                explicit.isNotEmpty() -> explicit.toInt()
                '<' in flags -> previous
                else -> next++
            }
            assertTrue(index > 0, "invalid printf argument in $text")
            previous = index
            result += index to (date + conversion)
        }
        return result
    }

    @Test fun nestedArgumentsCanMoveAcrossPluralClauses() {
        assertEquals(icuArguments("{total, plural, other {{off} of # off}}"),
            icuArguments("已关闭 {off} 项，共 {total} 项"))
        assertEquals(setOf("count", "names"), icuArguments("{count, plural, other {{names}}}"))
        assertEquals(setOf(1 to "s", 2 to "d"), printfArguments("%2\$d %1\$s %%"))
    }

    // Catch untranslated or moved resource names, malformed ICU and changed formatting arguments.
    @Test fun simplifiedChineseCoversEveryResourceAndPreservesArguments() {
        val root = File(System.getProperty("cleanyourtv.repoRoot") ?: error("no repo root"))
        val modules = listOf("app", "ui/design", "feature/connect", "feature/setup", "feature/manage",
            "feature/launcher", "feature/modules", "feature/backup", "tv/curtain")
        var checked = 0
        for (module in modules) {
            val resources = File(root, "$module/src/main/res")
            val englishFiles = File(resources, "values").listFiles { file ->
                file.name.startsWith("strings") && file.extension == "xml"
            } ?: error("no English resources in $module")
            for (englishFile in englishFiles) {
                val chineseFile = File(resources, "values-zh-rCN/${englishFile.name}")
                assertTrue(chineseFile.isFile, "missing ${chineseFile.path}")
                val english = read(englishFile)
                val chinese = read(chineseFile)
                assertTrue(chinese.keys.all { it in english }, "${chineseFile.path}: unknown resource names")
                for ((name, source) in english) {
                    if (!source.translatable && name !in chinese) continue
                    val translated = chinese[name] ?: fail("${chineseFile.path}: missing $name")
                    assertEquals(source.kind, translated.kind, "${chineseFile.path}: $name changed resource type")
                    for ((quantity, value) in translated.variants) {
                        val original = source.variants[quantity] ?: source.variants.getValue("other")
                        val label = "${chineseFile.path}: $name/$quantity"
                        assertTrue(value.isNotBlank(), "$label is blank")
                        try {
                            assertEquals(icuArguments(original), icuArguments(value), "$label changed ICU arguments")
                        } catch (error: IllegalArgumentException) {
                            fail("$label: ${error.message}")
                        }
                        assertEquals(printfArguments(original), printfArguments(value), "$label changed printf arguments")
                    }
                    checked++
                }
            }
        }
        assertTrue(checked > 1300, "expected the full Chinese resource set, checked $checked")
    }
}
