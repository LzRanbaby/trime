/*
 * SPDX-FileCopyrightText: 2026 GlassKeys contributors
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

package com.osfans.trime.ime.core

import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Build
import android.view.Window
import android.view.WindowManager
import timber.log.Timber

/**
 * GlassKeys: liquid-glass background blur for the IME window.
 *
 * This is an original implementation built directly on the public Android 12+
 * window blur APIs (see the AOSP "Window blurs" documentation). It does not
 * contain code from any other keyboard project.
 *
 * Behaviour:
 * - On API 31+ devices where the OEM has cross-window blur enabled, the IME
 *   window gets a background blur radius and a transparent window background,
 *   so the translucent glass color scheme shows a real-time frosted backdrop.
 * - Everywhere else this is a no-op: the keyboard simply keeps the
 *   semi-transparent colors of the glass theme (static frosted fallback).
 * - Any failure is swallowed so the blur can never crash the keyboard.
 */
object GlassBlurHelper {
    /** Background blur radius in pixels (AOSP samples use ~80-150 for frosted glass). */
    private const val BLUR_RADIUS_PX = 100

    fun applyTo(
        window: Window?,
        windowManager: WindowManager?,
    ) {
        try {
            if (window == null || windowManager == null) return
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
            if (!windowManager.isCrossWindowBlurEnabled) {
                Timber.d("GlassBlur: cross-window blur disabled by system/OEM, using static glass colors")
                return
            }
            // The blur is only visible through a translucent window background;
            // the keyboard itself paints semi-transparent glass colors on top.
            window.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
            window.setBackgroundBlurRadius(BLUR_RADIUS_PX)
            Timber.d("GlassBlur: background blur radius set to $BLUR_RADIUS_PX")
        } catch (e: Exception) {
            // Never let a cosmetic effect take the keyboard down.
            Timber.w(e, "GlassBlur: failed to apply background blur, continuing without it")
        }
    }
}
