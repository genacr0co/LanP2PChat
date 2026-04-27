package com.lanp2pchat;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.graphics.Color;
import android.view.Gravity;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private WebView webView;
    private TextView loadingText;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private static final String LOCAL_URL = "http://127.0.0.1:8765";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout root = new FrameLayout(this);

        loadingText = new TextView(this);
        loadingText.setText("Запуск LAN P2P Chat...");
        loadingText.setTextColor(Color.WHITE);
        loadingText.setTextSize(18);
        loadingText.setGravity(Gravity.CENTER);
        loadingText.setBackgroundColor(Color.rgb(15, 23, 42));

        root.addView(
            loadingText,
            new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        );

        webView = new WebView(this);
        webView.setVisibility(WebView.GONE);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);

        webView.setWebViewClient(new WebViewClient());

        root.addView(
            webView,
            new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        );

        setContentView(root);

        startPythonBackend();
    }

    private void startPythonBackend() {
        new Thread(() -> {
            try {
                File staticDir = new File(getFilesDir(), "static");
                copyAssetsToDir("", staticDir);

                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(this));
                }

                Python py = Python.getInstance();

                String dataDir = getFilesDir().getAbsolutePath();
                String staticPath = staticDir.getAbsolutePath();

                Object result = py.getModule("android_server")
                    .callAttr("start", dataDir, staticPath);

                String text = String.valueOf(result);

                if (!"ok".equals(text)) {
                    showError(text);
                    return;
                }

                waitForBackendAndOpen();

            } catch (Exception e) {
                showError(e.toString());
            }
        }).start();
    }

    private void waitForBackendAndOpen() {
        for (int i = 0; i < 60; i++) {
            try {
                java.net.URL url = new java.net.URL(LOCAL_URL + "/api/me");
                java.net.HttpURLConnection conn =
                    (java.net.HttpURLConnection) url.openConnection();

                conn.setConnectTimeout(1000);
                conn.setReadTimeout(1000);

                int code = conn.getResponseCode();
                conn.disconnect();

                if (code == 200) {
                    openWebView();
                    return;
                }

            } catch (Exception ignored) {}

            try {
                Thread.sleep(500);
            } catch (InterruptedException ignored) {}
        }

        showError("Backend не запустился");
    }

    private void openWebView() {
        handler.post(() -> {
            loadingText.setVisibility(TextView.GONE);
            webView.setVisibility(WebView.VISIBLE);
            webView.loadUrl(LOCAL_URL);
        });
    }

    private void showError(String error) {
        handler.post(() -> {
            loadingText.setText("Ошибка запуска:\n\n" + error);
            loadingText.setTextColor(Color.RED);
        });
    }

    private void copyAssetsToDir(String assetPath, File outDir) throws Exception {
        if (!outDir.exists()) {
            outDir.mkdirs();
        }

        String[] assets = getAssets().list(assetPath);

        if (assets == null) {
            return;
        }

        for (String asset : assets) {
            String childAssetPath = assetPath.isEmpty()
                ? asset
                : assetPath + "/" + asset;

            String[] children = getAssets().list(childAssetPath);

            if (children != null && children.length > 0) {
                File childDir = new File(outDir, asset);
                copyAssetsToDir(childAssetPath, childDir);
            } else {
                File outFile = new File(outDir, asset);
                copyAssetFile(childAssetPath, outFile);
            }
        }
    }

    private void copyAssetFile(String assetPath, File outFile) throws Exception {
        InputStream input = getAssets().open(assetPath);

        File parent = outFile.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }

        OutputStream output = new FileOutputStream(outFile);

        byte[] buffer = new byte[8192];
        int length;

        while ((length = input.read(buffer)) > 0) {
            output.write(buffer, 0, length);
        }

        output.flush();
        output.close();
        input.close();
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}