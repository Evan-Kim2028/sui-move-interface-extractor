module fixture::test_module {
    struct SimpleStruct has drop {
        value: u64
    }

    public fun simple_func(x: u64): u64 {
        x
    }
}
