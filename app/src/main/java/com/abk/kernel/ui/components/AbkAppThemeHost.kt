package com.abk.kernel.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.abk.kernel.data.repository.PreferencesRepository
import com.abk.kernel.ui.theme.AbkTheme

/** Applies the app theme plus the shared background/surface-alpha host around [content]. */
@Composable
fun AbkAppThemeHost(
    themeMode: String,
    dynamicColorEnabled: Boolean,
    customThemeColorArgb: Int?,
    customAccentColorArgb: Int?,
    backgroundUri: String?,
    backgroundEnabled: Boolean,
    uiSurfaceAlpha: Float,
    content: @Composable () -> Unit
) {
    AbkTheme(
        themeMode = themeMode,
        dynamicColorEnabled = dynamicColorEnabled,
        customThemeColorArgb = customThemeColorArgb,
        customAccentColorArgb = customAccentColorArgb
    ) {
        AppBackgroundHost(
            backgroundUri = backgroundUri,
            backgroundEnabled = backgroundEnabled,
            uiSurfaceAlpha = uiSurfaceAlpha,
            content = content
        )
    }
}

/** [AbkAppThemeHost] driven directly by the persisted appearance preferences. */
@Composable
fun AbkAppThemeHost(prefs: PreferencesRepository, content: @Composable () -> Unit) {
    val themeMode by prefs.themeMode.collectAsState(initial = "dark")
    val dynamicColorEnabled by prefs.dynamicColorEnabled.collectAsState(initial = true)
    val customThemeColorArgb by prefs.customThemeColorArgb.collectAsState(initial = null)
    val customAccentColorArgb by prefs.customAccentColorArgb.collectAsState(initial = null)
    val customBackgroundUri by prefs.customBackgroundUri.collectAsState(initial = null)
    val backgroundImageEnabled by prefs.backgroundImageEnabled.collectAsState(initial = false)
    val uiSurfaceAlpha by prefs.uiSurfaceAlpha.collectAsState(initial = 1f)

    AbkAppThemeHost(
        themeMode = themeMode,
        dynamicColorEnabled = dynamicColorEnabled,
        customThemeColorArgb = customThemeColorArgb,
        customAccentColorArgb = customAccentColorArgb,
        backgroundUri = customBackgroundUri,
        backgroundEnabled = backgroundImageEnabled,
        uiSurfaceAlpha = uiSurfaceAlpha,
        content = content
    )
}
