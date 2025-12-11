package com.gdemo.util

import android.util.Log

object AnalyticsLogger {
    private const val TAG = "GdeMoe"

    fun event(name: String, params: Map<String, Any?> = emptyMap()) {
        Log.d(TAG, "event=$name params=$params")
    }

    fun screen(name: String) {
        Log.d(TAG, "screen=$name")
    }

    fun debug(message: String, params: Map<String, Any?> = emptyMap()) {
        Log.d(TAG, "$message params=$params")
    }
}
