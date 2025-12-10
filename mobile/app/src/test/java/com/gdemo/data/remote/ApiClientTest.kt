package com.gdemo.data.remote

import org.junit.Assert.assertEquals
import org.junit.Test

class ApiClientTest {
    @Test
    fun `sanitize adds scheme and trailing slash`() {
        assertEquals("http://example.com/", ApiClient.sanitizeBaseUrl("example.com"))
        assertEquals("http://example.com/", ApiClient.sanitizeBaseUrl("http://example.com"))
        assertEquals("https://example.com/", ApiClient.sanitizeBaseUrl("https://example.com"))
        assertEquals("http://192.168.50.90:8000/", ApiClient.sanitizeBaseUrl("192.168.50.90:8000"))
        assertEquals("http://192.168.50.90:8000/", ApiClient.sanitizeBaseUrl("http://192.168.50.90:8000/"))
    }
}
