package com.abk.kernel.utils

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Log
import android.widget.Toast
import com.abk.kernel.R

private const val TAG = "ExternalLinks"

/**
 * Opens [url] in an external app and reports the failure to the user instead of doing nothing when
 * no handler is available. Returns whether the link was handed off successfully.
 */
fun Context.openExternalLink(url: String): Boolean {
    val target = url.trim()
    if (target.isEmpty()) {
        reportLinkFailure(target, IllegalArgumentException("blank url"))
        return false
    }
    return runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(target))) }
        .onFailure { reportLinkFailure(target, it) }
        .isSuccess
}

/**
 * Runs [open] (typically `UriHandler.openUri`) and reports the failure to the user when the link
 * cannot be handled. Returns whether the link was handed off successfully.
 */
fun Context.openExternalLink(url: String, open: (String) -> Unit): Boolean {
    val target = url.trim()
    if (target.isEmpty()) {
        reportLinkFailure(target, IllegalArgumentException("blank url"))
        return false
    }
    return runCatching { open(target) }
        .onFailure { reportLinkFailure(target, it) }
        .isSuccess
}

private fun Context.reportLinkFailure(url: String, error: Throwable) {
    Log.w(TAG, "Failed to open external link: $url", error)
    Toast.makeText(this, getString(R.string.open_link_failed), Toast.LENGTH_SHORT).show()
}
