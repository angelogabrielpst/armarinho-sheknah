"use strict";

const STORAGE_KEYS = {
  cart: "pontoPapel.cart",
  clientId: "pontoPapel.clientId",
};
const DEFAULT_WHATSAPP = "5531989319971";
const starterProducts = [
  { id: "starter-1", name: "Caderno Meu Lugar", category: "Cadernos", price: 42.9, description: "Um espaço todo seu para ideias, planos e rabiscos.", symbol: "✳" },
  { id: "starter-2", name: "Kit Canetas Jardim", category: "Escrita", price: 24.9, description: "Cores bonitas para deixar cada palavra especial.", symbol: "✿" },
  { id: "starter-3", name: "Planner da Semana", category: "Organização", price: 36.5, description: "Organize seus dias com leveza e um toque de cor.", symbol: "☼" },
  { id: "starter-4", name: "Bloco Boas Ideias", category: "Criatividade", price: 18.9, description: "Para aquela ideia boa que aparece de repente.", symbol: "♡" },
  { id: "starter-5", name: "Marca-páginas Flores", category: "Presentes", price: 12.5, description: "Um carinho para acompanhar a próxima leitura.", symbol: "❀" },
  { id: "starter-6", name: "Estojo Dia Feliz", category: "Organização", price: 32.9, description: "Seu material favorito sempre por perto.", symbol: "✦" },
  { id: "starter-7", name: "Cartões para Presentear", category: "Presentes", price: 16.9, description: "Palavras escritas à mão fazem toda a diferença.", symbol: "♡" },
  { id: "starter-8", name: "Aquarela Pequenos Mundos", category: "Criatividade", price: 49.9, description: "Um convite colorido para experimentar e criar.", symbol: "✿" },
];
const instagramPosts = [
  { code: "De_5EZhoGfd", caption: "Enfeites de Natal 🌲🎁☃️", image: "post-01.webp", alt: "Enfeites de Natal" },
  { code: "De_3bGsIFiN", caption: "Brilho labial 💄✨", image: "post-02.webp", alt: "Brilho labial" },
  { code: "DcjUa3WIF5G", caption: "Chapéus country 👒", image: "post-03.webp", alt: "Chapéu country" },
  { code: "DcjUOltIHCQ", caption: "Meia calça infantil - bebê", image: "post-04.webp", alt: "Meia-calça infantil para bebê" },
  { code: "DcjUBKHoHDT", caption: "Meias de bebê 🍼🩷🩵", image: "post-05.webp", alt: "Meias de bebê" },
  { code: "DcjIgvIoH_9", caption: "Fones bluetooth", image: "post-06.webp", alt: "Fones Bluetooth" },
  { code: "DcjH-L1PYGW", caption: "Limpa contato", image: "post-07.webp", alt: "Produto limpa-contato" },
  { code: "DcjHz6toFk2", caption: "Bonés 🧢", image: "post-08.webp", alt: "Bonés" },
  { code: "DcjHmgDIBd7", caption: "Boias circular 🏊🏻", image: "post-09.webp", alt: "Boias para piscina" },
  { code: "Dci-whtBikD", caption: "Cartinha de colecionador - BTS 💜", image: "post-10.webp", alt: "Cartinha colecionável do BTS" },
  { code: "Dci-fj6PpfM", caption: "Casinha de bonecas 🩷", image: "post-11.webp", alt: "Casinha de bonecas" },
  { code: "Dci8RGPnBDc", caption: "Chinelo Atlético e Cruzeiro ⚽", image: "post-12.webp", alt: "Chinelos dos times Atlético e Cruzeiro" },
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
const API_BASE_URL = String((window.APP_CONFIG || {}).apiBaseUrl || "").replace(/\/$/, "");
const readStored = (key, fallback) => {
  try {
    const stored = localStorage.getItem(key);
    return stored === null ? fallback : JSON.parse(stored);
  } catch (error) {
    console.error(`Não foi possível ler ${key} do armazenamento local.`, error);
    return fallback;
  }
};
const writeStored = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error(`Não foi possível salvar ${key} no armazenamento local.`, error);
    showToast("Não foi possível salvar. Verifique o espaço disponível no navegador.");
    return false;
  }
};

let products = [];
let whatsappNumber = DEFAULT_WHATSAPP;
let adminToken = sessionStorage.getItem("pontoPapel.adminToken") || "";
let clientId = localStorage.getItem(STORAGE_KEYS.clientId);
if (!clientId) {
  clientId = crypto.randomUUID ? crypto.randomUUID() : `client-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem(STORAGE_KEYS.clientId, clientId);
}
let cart = readStored(STORAGE_KEYS.cart, []);
if (!Array.isArray(cart)) cart = [];
let activeCategory = "Todos";
let toastTimer;

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (adminToken) headers["X-Admin-Token"] = adminToken;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Não foi possível concluir a operação.");
  return data;
}

async function loadWebsiteData() {
  try {
    const [loadedProducts, settings, serverCart] = await Promise.all([
      apiRequest("/api/products"),
      apiRequest("/api/settings"),
      apiRequest(`/api/cart?client_id=${encodeURIComponent(clientId)}`),
    ]);
    products = Array.isArray(loadedProducts) ? loadedProducts : [];
    whatsappNumber = settings.whatsapp || DEFAULT_WHATSAPP;
    if (serverCart.length) {
      cart = serverCart;
      writeStored(STORAGE_KEYS.cart, cart);
    } else {
      cart = cart.filter((entry) => products.some((product) => product.id === entry.id));
      await persistCart();
    }
  } catch (error) {
    console.error(error);
    if (!API_BASE_URL) {
      products = starterProducts;
      whatsappNumber = DEFAULT_WHATSAPP;
    }
    showToast("Não foi possível carregar os dados da loja.");
  }
  renderProducts();
  renderAdminProducts();
  renderCart();
}

const formatPrice = (value) => Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function productImageUrl(image) {
  if (!image || /^(https?:|data:|blob:)/i.test(image) || !API_BASE_URL) return image;
  return `${API_BASE_URL}/${image.replace(/^\/+/, "")}`;
}

function productImage(product, extraClass = "") {
  if (product.image) return `<img class="product-image ${extraClass}" src="${escapeHtml(productImageUrl(product.image))}" alt="${escapeHtml(product.name)}" loading="lazy">`;
  const tone = Number(String(product.id).replace(/\D/g, "").slice(-1) || 0) % 4;
  return `<div class="product-placeholder tone-${tone} ${extraClass}" role="img" aria-label="${escapeHtml(product.name)}">${escapeHtml(product.symbol || "✳")}</div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function renderCategories() {
  const categories = ["Todos", ...new Set(products.map((product) => product.category).filter(Boolean))];
  if (activeCategory !== "Todos" && !categories.includes(activeCategory)) activeCategory = "Todos";
  $("#categoryList").innerHTML = categories.map((category) => `
    <button class="category-button ${category === activeCategory ? "active" : ""}" type="button" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>
  `).join("");
}

function renderProducts() {
  renderCategories();
  const query = $("#productSearch").value.trim().toLocaleLowerCase("pt-BR");
  const visibleProducts = products.filter((product) => {
    const matchesCategory = activeCategory === "Todos" || product.category === activeCategory;
    const matchesQuery = `${product.name} ${product.category} ${product.description || ""}`.toLocaleLowerCase("pt-BR").includes(query);
    return matchesCategory && matchesQuery;
  });
  $("#productGrid").innerHTML = visibleProducts.map((product) => `
    <article class="product-card">
      <div class="product-image-wrap">
        ${productImage(product)}
        ${product.isNew ? '<span class="product-badge">NOVIDADE</span>' : ""}
        <button class="quick-add" type="button" data-add="${escapeHtml(product.id)}" aria-label="Adicionar ${escapeHtml(product.name)} à sacola">+</button>
      </div>
      <div class="product-info">
        <span class="product-category">${escapeHtml(product.category || "Papelaria")}</span>
        <h3>${escapeHtml(product.name)}</h3>
        ${product.description ? `<p class="product-description">${escapeHtml(product.description)}</p>` : ""}
        <span class="product-price">${formatPrice(product.price)}</span>
      </div>
    </article>
  `).join("");
  $("#emptyState").hidden = visibleProducts.length > 0;
}

function renderInstagramPosts() {
  $("#instagramGrid").innerHTML = instagramPosts.map((post) => `
    <article class="instagram-card">
      <a class="instagram-image-link" href="https://www.instagram.com/p/${post.code}/" target="_blank" rel="noopener noreferrer" aria-label="Ver publicação: ${escapeHtml(post.caption)}">
        <img src="assets/instagram/${post.image}" alt="${escapeHtml(post.alt)}" loading="lazy">
        <span class="instagram-overlay">Ver publicação <span>↗</span></span>
      </a>
      <div class="instagram-card-copy">
        <span class="instagram-handle">@armarinhosheknah</span>
        <p>${escapeHtml(post.caption)}</p>
        <a href="https://www.instagram.com/p/${post.code}/" target="_blank" rel="noopener noreferrer">Ver no Instagram ↗</a>
      </div>
    </article>
  `).join("");
}

async function persistCart() {
  await apiRequest("/api/cart", {
    method: "POST",
    body: JSON.stringify({ client_id: clientId, items: cart }),
  });
}

function saveCart() {
  writeStored(STORAGE_KEYS.cart, cart);
  renderCart();
  persistCart().catch((error) => {
    console.error(error);
    showToast("A sacola não foi sincronizada com o servidor.");
  });
}

function addToCart(id) {
  const product = products.find((item) => item.id === id);
  if (!product) return;
  const existing = cart.find((item) => item.id === id);
  if (existing) existing.quantity += 1;
  else cart.push({ id, quantity: 1 });
  saveCart();
  showToast(`${product.name} adicionado à sacola!`);
}

function updateQuantity(id, amount) {
  const item = cart.find((entry) => entry.id === id);
  if (!item) return;
  item.quantity += amount;
  if (item.quantity <= 0) cart = cart.filter((entry) => entry.id !== id);
  saveCart();
}

function renderCart() {
  cart = cart.filter((entry) => products.some((product) => product.id === entry.id) && Number(entry.quantity) > 0);
  const count = cart.reduce((total, item) => total + item.quantity, 0);
  const items = cart.map((entry) => ({ ...entry, product: products.find((item) => item.id === entry.id) }));
  const subtotal = items.reduce((total, entry) => total + Number(entry.product.price) * entry.quantity, 0);
  $("#cartCount").textContent = count;
  $("#drawerItemCount").textContent = count ? `(${count})` : "";
  $("#cartSubtotal").textContent = formatPrice(subtotal);
  $("#cartEmpty").hidden = count > 0;
  $("#cartFooter").hidden = count === 0;
  $("#cartItems").innerHTML = items.map(({ product, quantity }) => `
    <div class="cart-item">
      ${productImage(product, "cart-item-image")}
      <div class="cart-item-detail">
        <h3>${escapeHtml(product.name)}</h3><span>${formatPrice(product.price)}</span>
        <div class="quantity-control">
          <button type="button" data-quantity="${escapeHtml(product.id)}" data-change="-1" aria-label="Diminuir quantidade">−</button>
          <span>${quantity}</span>
          <button type="button" data-quantity="${escapeHtml(product.id)}" data-change="1" aria-label="Aumentar quantidade">+</button>
        </div>
      </div>
      <button class="remove-item" type="button" data-remove="${escapeHtml(product.id)}" aria-label="Remover ${escapeHtml(product.name)}">×</button>
    </div>
  `).join("");
}

function openCart() {
  $("#overlay").classList.add("visible");
  $("#cartDrawer").classList.add("open");
  $("#cartDrawer").setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  $("#cartOpen").setAttribute("aria-expanded", "true");
}

function closeCart() {
  $("#overlay").classList.remove("visible");
  $("#cartDrawer").classList.remove("open");
  $("#cartDrawer").setAttribute("aria-hidden", "true");
  if (!$("#adminModal").classList.contains("visible")) document.body.classList.remove("modal-open");
  $("#cartOpen").setAttribute("aria-expanded", "false");
}

function openAdmin() {
  $("#adminModal").classList.add("visible");
  $("#adminModal").setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  if (adminToken) showAdminContent();
  else window.setTimeout(() => $("#adminPassword").focus(), 100);
}

function closeAdmin() {
  $("#adminModal").classList.remove("visible");
  $("#adminModal").setAttribute("aria-hidden", "true");
  if (!$("#cartDrawer").classList.contains("open")) document.body.classList.remove("modal-open");
}

function showAdminContent() {
  $("#adminLogin").hidden = true;
  $("#adminContent").hidden = false;
  $("#whatsappNumber").value = whatsappNumber;
  renderAdminProducts();
}

function renderAdminProducts() {
  $("#adminProductCount").textContent = `${products.length} ${products.length === 1 ? "item" : "itens"}`;
  $("#adminProductList").innerHTML = products.map((product) => `
    <div class="admin-product-row">
      ${product.image ? `<img src="${escapeHtml(productImageUrl(product.image))}" alt="">` : `<div class="product-placeholder">${escapeHtml(product.symbol || "✳")}</div>`}
      <div><strong>${escapeHtml(product.name)}</strong><small>${escapeHtml(product.category || "Papelaria")} · ${formatPrice(product.price)}</small></div>
      <button class="delete-product" type="button" data-delete="${escapeHtml(product.id)}">Excluir</button>
    </div>
  `).join("");
}

async function checkout() {
  const phone = String(whatsappNumber || DEFAULT_WHATSAPP).replace(/\D/g, "");
  if (!phone) {
    showToast("A loja ainda não configurou o WhatsApp. Avise o administrador.");
    return;
  }
  if (phone.length < 12 || phone.length > 13) {
    showToast("O WhatsApp da loja precisa incluir o código do país e o DDD.");
    return;
  }
  const lines = cart.map((entry) => {
    const product = products.find((item) => item.id === entry.id);
    return `• ${entry.quantity}x ${product.name} — ${formatPrice(product.price * entry.quantity)}`;
  });
  const total = cart.reduce((sum, entry) => {
    const product = products.find((item) => item.id === entry.id);
    return sum + product.price * entry.quantity;
  }, 0);
  const message = `Olá! Gostaria de fazer este pedido:\n\n${lines.join("\n")}\n\n*Total dos produtos: ${formatPrice(total)}*\n\nPodemos combinar o pagamento e a entrega?`;
  try {
    await apiRequest("/api/orders", {
      method: "POST",
      body: JSON.stringify({
        subtotal: total,
        items: cart.map((entry) => {
          const product = products.find((item) => item.id === entry.id);
          return { id: product.id, name: product.name, price: product.price, quantity: entry.quantity };
        }),
      }),
    });
  } catch (error) {
    console.error(error);
  }
  window.open(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`, "_blank", "noopener,noreferrer");
}

function readImageAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Não foi possível ler a imagem selecionada."));
    reader.readAsDataURL(file);
  });
}

$("#productGrid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-add]");
  if (button) addToCart(button.dataset.add);
});
$("#categoryList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  activeCategory = button.dataset.category;
  renderProducts();
});
$("#productSearch").addEventListener("input", renderProducts);
$("#cartOpen").addEventListener("click", openCart);
$("#overlay").addEventListener("click", closeCart);
$$("[data-close]").forEach((button) => button.addEventListener("click", closeCart));
$("#keepShopping").addEventListener("click", closeCart);
$("#cartItems").addEventListener("click", (event) => {
  const quantityButton = event.target.closest("[data-quantity]");
  const removeButton = event.target.closest("[data-remove]");
  if (quantityButton) updateQuantity(quantityButton.dataset.quantity, Number(quantityButton.dataset.change));
  if (removeButton) {
    cart = cart.filter((item) => item.id !== removeButton.dataset.remove);
    saveCart();
  }
});
$("#checkoutButton").addEventListener("click", checkout);
$("#adminOpen").addEventListener("click", openAdmin);
$$("[data-close-admin]").forEach((button) => button.addEventListener("click", closeAdmin));
$("#adminModal").addEventListener("click", (event) => {
  if (event.target === $("#adminModal")) closeAdmin();
});
$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const result = await apiRequest("/api/admin/login", {
      method: "POST",
      body: JSON.stringify({ password: $("#adminPassword").value }),
    });
    adminToken = result.token;
    sessionStorage.setItem("pontoPapel.adminToken", adminToken);
    showAdminContent();
  } catch (error) {
    showToast(error.message);
    $("#adminPassword").select();
  }
});
$("#productForm").addEventListener("change", async (event) => {
  if (event.target.name !== "image") return;
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    event.target.value = "";
    $("#imagePreview").innerHTML = "<span>Imagem maior que 2 MB. Escolha um arquivo menor.</span>";
    return;
  }
  try {
    const dataUrl = await readImageAsDataUrl(file);
    $("#imagePreview").innerHTML = `<img src="${dataUrl}" alt="Prévia da imagem selecionada">`;
  } catch (error) {
    console.error(error);
    showToast("Não foi possível abrir essa imagem.");
  }
});
$("#productForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const file = data.get("image");
  if (!(file instanceof File) || !file.size) {
    showToast("Selecione uma imagem para o produto.");
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    showToast("A imagem deve ter no máximo 2 MB.");
    return;
  }
  try {
    const image = await readImageAsDataUrl(file);
    const product = {
      id: `product-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: String(data.get("name")).trim(),
      price: Number(data.get("price")),
      category: String(data.get("category")),
      description: String(data.get("description")).trim(),
      image,
    };
    if (!product.name || !Number.isFinite(product.price) || product.price <= 0) {
      showToast("Confira o nome e o preço do produto.");
      return;
    }
    await apiRequest("/api/products", {
      method: "POST",
      body: JSON.stringify(product),
    });
    await loadWebsiteData();
    form.reset();
    $("#imagePreview").innerHTML = "<span>Prévia da imagem</span>";
    renderProducts();
    renderAdminProducts();
    showToast("Produto adicionado ao catálogo!");
  } catch (error) {
    console.error(error);
    showToast("Não foi possível adicionar o produto.");
  }
});
$("#adminProductList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-delete]");
  if (!button) return;
  const product = products.find((item) => item.id === button.dataset.delete);
  if (!product || !window.confirm(`Remover "${product.name}" do catálogo?`)) return;
  apiRequest(`/api/product?id=${encodeURIComponent(product.id)}`, { method: "DELETE" })
    .then(() => loadWebsiteData())
    .catch((error) => showToast(error.message));
  cart = cart.filter((item) => item.id !== product.id);
  writeStored(STORAGE_KEYS.cart, cart);
  renderProducts();
  renderAdminProducts();
  renderCart();
  showToast("Produto removido.");
});
$("#storeSettings").addEventListener("submit", (event) => {
  event.preventDefault();
  const phone = $("#whatsappNumber").value.replace(/\D/g, "");
  if (phone.length < 12 || phone.length > 13) {
    showToast("Use o formato com país e DDD. Ex.: 5511999999999.");
    return;
  }
  apiRequest("/api/settings/whatsapp", {
    method: "PUT",
    body: JSON.stringify({ whatsapp: phone }),
  }).then((settings) => {
    whatsappNumber = settings.whatsapp;
    showToast("WhatsApp da loja salvo!");
  }).catch((error) => showToast(error.message));
});
$("#logoutButton").addEventListener("click", () => {
  adminToken = "";
  sessionStorage.removeItem("pontoPapel.adminToken");
  $("#adminContent").hidden = true;
  $("#adminLogin").hidden = false;
  $("#loginForm").reset();
  showToast("Você saiu do modo administrador.");
});
$("#menuToggle").addEventListener("click", () => {
  const isOpen = $("#mainNav").classList.toggle("open");
  $("#menuToggle").setAttribute("aria-expanded", String(isOpen));
  $("#menuToggle").setAttribute("aria-label", isOpen ? "Fechar menu" : "Abrir menu");
});
$$(".main-nav a").forEach((link) => link.addEventListener("click", () => {
  $("#mainNav").classList.remove("open");
  $("#menuToggle").setAttribute("aria-expanded", "false");
}));
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  closeCart();
  closeAdmin();
});

$("#currentYear").textContent = new Date().getFullYear();
$("#adminLoginHint").textContent = API_BASE_URL
  ? "Acesso protegido pela senha configurada no servidor."
  : "Acesso inicial: admin123 · Defina ADMIN_PASSWORD no servidor antes de publicar.";
renderInstagramPosts();
loadWebsiteData();
