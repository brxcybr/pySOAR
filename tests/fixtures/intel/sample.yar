rule sample_hash_rule {
    meta:
        description = "Sample YARA rule"
    strings:
        $hash = "d41d8cd98f00b204e9800998ecf8427e"
    condition:
        $hash
}
