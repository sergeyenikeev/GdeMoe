package com.gdemo.util

import android.content.Context
import android.os.Build
import android.util.Log
import com.gdemo.data.local.loadConnection
import com.gdemo.data.remote.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

object AnalyticsLogger {
    private const val TAG = "GdeMoe"
    private var appContext: Context? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val client = OkHttpClient.Builder().build()

    fun init(context: Context) {
        appContext = context.applicationContext
    }

    fun event(name: String, params: Map<String, Any?> = emptyMap()) {
        Log.d(TAG, "event=$name params=$params")
        sendRemote(level = "info", name = name, params = params)
    }

    fun screen(name: String) {
        Log.d(TAG, "screen=$name")
        sendRemote(level = "info", name = "screen", params = mapOf("screen" to name))
    }

    fun debug(message: String, params: Map<String, Any?> = emptyMap()) {
        Log.d(TAG, "$message params=$params")
        sendRemote(level = "debug", name = message, params = params)
    }

    private fun sendRemote(level: String, name: String, params: Map<String, Any?>) {
        val ctx = appContext ?: return
        scope.launch {
            runCatching {
                val settings = ctx.loadConnection()
                val base = ApiClient.sanitizeBaseUrl(settings.baseUrl).trimEnd('/')
                val json = JSONObject()
                json.put("name", name)
                json.put("level", level)
                json.put("device", Build.MODEL)
                json.put("created_at", System.currentTimeMillis())
                val paramsJson = JSONObject()
                params.forEach { paramsJson.put(it.key, it.value?.toString()) }
                json.put("params", paramsJson)
                val body = json.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("$base/api/v1/logs/")
                    .post(body)
                    .build()
                client.newCall(request).execute().close()
            }.onFailure {
                Log.d(TAG, "log_send_failed ${it.localizedMessage}")
            }
        }
    }
}
