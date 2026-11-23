fn main() {
    println!("cargo:rerun-if-changed=src/alignment.cpp");
    println!("cargo:rerun-if-changed=../porechop/src/alignment.cpp");
    println!("cargo:rerun-if-changed=../porechop/include");
    cc::Build::new()
        .cpp(true)
        .std("c++14")
        .define("NDEBUG", None)
        .include("../porechop/include")
        .file("src/alignment.cpp")
        .file("../porechop/src/alignment.cpp")
        .compile("porechop_alignment");
}
