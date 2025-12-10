package com.gdemo

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.gdemo.data.model.SharedContent
import com.gdemo.ui.navigation.GdeNavHost
import com.gdemo.ui.theme.GdeMoeTheme

class MainActivity : ComponentActivity() {
    private var sharedContent: SharedContent? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sharedContent = extractSharedContent(intent)
        setContent {
            GdeMoeApp(sharedContent)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        sharedContent = extractSharedContent(intent)
        setContent { GdeMoeApp(sharedContent) }
    }

    private fun extractSharedContent(intent: Intent?): SharedContent? {
        if (intent?.action == Intent.ACTION_SEND) {
            val type = intent.type
            if (type == "text/plain") {
                val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: return null
                val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT)
                val url = findFirstUrl(text) ?: return null
                val titleCandidate = subject ?: text.replace(url, "").trim().takeIf { it.isNotBlank() }
                return SharedContent(url = url, title = titleCandidate)
            }
            val stream: Uri? = intent.getParcelableExtra(Intent.EXTRA_STREAM)
            if (stream != null) {
                val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT)
                return SharedContent(
                    fileUri = stream.toString(),
                    mimeType = type,
                    title = subject
                )
            }
        }
        return null
    }

    private fun findFirstUrl(text: String): String? {
        val regex = "(https?://\\S+)".toRegex()
        return regex.find(text)?.value
    }
}

@Composable
fun GdeMoeApp(sharedContent: SharedContent? = null) {
    var isOnboarded by remember { mutableStateOf(sharedContent != null) }
    GdeMoeTheme {
        Surface {
            GdeNavHost(
                isOnboarded = isOnboarded,
                onFinishOnboarding = { isOnboarded = true },
                sharedContent = sharedContent
            )
        }
    }
}
