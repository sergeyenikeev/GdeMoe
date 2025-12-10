package com.gdemo.data.local

import android.content.Context

private const val PREFS_NAME = "gdemoe_prefs"
private const val KEY_BASE_URL = "base_url"
private const val KEY_LOGIN = "login"
private const val KEY_PASSWORD = "password"
private const val KEY_SCOPE = "scope"

data class ConnectionSettings(
    val baseUrl: String,
    val login: String,
    val password: String,
    val scope: String
)

fun Context.connectionPrefs() = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

fun Context.loadConnection(): ConnectionSettings =
    ConnectionSettings(
        baseUrl = connectionPrefs().getString(KEY_BASE_URL, "http://192.168.50.90:8000") ?: "http://192.168.50.90:8000",
        login = connectionPrefs().getString(KEY_LOGIN, "demo@local") ?: "demo@local",
        password = connectionPrefs().getString(KEY_PASSWORD, "noop") ?: "noop",
        scope = connectionPrefs().getString(KEY_SCOPE, "public") ?: "public"
    )

fun Context.saveConnection(settings: ConnectionSettings) {
    connectionPrefs().edit()
        .putString(KEY_BASE_URL, settings.baseUrl)
        .putString(KEY_LOGIN, settings.login)
        .putString(KEY_PASSWORD, settings.password)
        .putString(KEY_SCOPE, settings.scope)
        .apply()
}
