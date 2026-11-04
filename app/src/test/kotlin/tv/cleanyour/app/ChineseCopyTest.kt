package tv.cleanyour.app

import android.icu.text.MessageFormat
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.File
import java.util.Locale
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.fail

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], application = android.app.Application::class)
class ChineseCopyTest {
    private data class Copy(val text: String, val translatable: Boolean)
    private val string = Regex("<string name=\"([a-z0-9_]+)\"([^>]*)>(.*?)</string>", RegexOption.DOT_MATCHES_ALL)

    private fun read(file: File): Map<String, Copy> {
        val result = linkedMapOf<String, Copy>()
        for (match in string.findAll(file.readText())) {
            val (name, attributes, raw) = match.destructured
            val text = raw.replace("\\'", "'").replace("\\\"", "\"")
                .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            assertTrue(name !in result, "${file.path}: duplicate $name")
            result[name] = Copy(text, "translatable=\"false\"" !in attributes)
        }
        return result
    }

    // Catch new untranslated copy, moved resource names and broken ICU patterns during upstream syncs.
    @Test fun simplifiedChineseCoversEveryResourceAndPreservesIcuArguments() {
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
                    assertTrue(translated.text.isNotBlank(), "${chineseFile.path}: blank $name")
                    try {
                        val sourceFormat = MessageFormat(source.text, Locale.ENGLISH)
                        val translatedFormat = MessageFormat(translated.text, Locale.SIMPLIFIED_CHINESE)
                        assertEquals(sourceFormat.argumentNames, translatedFormat.argumentNames,
                            "${chineseFile.path}: $name changed ICU arguments")
                    } catch (error: IllegalArgumentException) {
                        fail("${chineseFile.path}: $name: ${error.message}")
                    }
                    checked++
                }
            }
        }
        assertTrue(checked > 1300, "expected the full Chinese resource set, checked $checked")
    }
}
