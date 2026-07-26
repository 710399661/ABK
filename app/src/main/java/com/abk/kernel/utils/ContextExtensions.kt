package com.abk.kernel.utils

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import android.widget.Toast

/** Resolves the hosting [Activity] when [Context] is wrapped (e.g. [ContextThemeWrapper]). */
tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

/** Puts [text] on the clipboard, optionally confirming with a short toast. */
fun Context.copyToClipboard(label: String, text: String, toastMessage: String? = null) {
    val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
    if (toastMessage != null) {
        Toast.makeText(this, toastMessage, Toast.LENGTH_SHORT).show()
    }
}

/** Opens [url] in an external viewer, ignoring blank urls and missing handlers. */
fun Context.openExternalUrl(url: String) {
    if (url.isBlank()) return
    runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
}
