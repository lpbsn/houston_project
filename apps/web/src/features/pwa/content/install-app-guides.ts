import type { LucideIcon } from 'lucide-react'
import {
  Apple,
  ArrowDown,
  Check,
  Globe,
  Home,
  Menu,
  MonitorSmartphone,
  MoreVertical,
  Plus,
  Settings,
  Share,
  Smartphone,
} from 'lucide-react'

export type InstallPlatform = 'ios' | 'android'

export type InstallStep = {
  id: string
  text: string
  icon: LucideIcon
  number?: number
}

export type InstallBrowserGuide = {
  id: string
  title: string
  icon?: LucideIcon
  steps: InstallStep[]
  footnote?: string
}

export const INSTALL_APP_FOOTER_NOTE =
  'Une fois installée, Spore se lance en plein écran comme une vraie application.'

export const INSTALL_APP_GUIDES: Record<InstallPlatform, InstallBrowserGuide[]> = {
  ios: [
    {
      id: 'safari',
      title: 'Avec Safari',
      icon: Globe,
      steps: [
        {
          id: 'safari-1',
          number: 1,
          icon: Share,
          text: 'Appuyez sur le bouton Partager — le carré avec une flèche vers le haut.',
        },
        {
          id: 'safari-2',
          number: 2,
          icon: ArrowDown,
          text: 'Faites défiler les options.',
        },
        {
          id: 'safari-3',
          number: 3,
          icon: Plus,
          text: "Appuyez sur Ajouter à l'écran d'accueil.",
        },
        {
          id: 'safari-4',
          number: 4,
          icon: Check,
          text: "Vérifiez que l'option Ouvrir comme app web est activée, si elle apparaît, puis appuyez sur Ajouter.",
        },
        {
          id: 'safari-5',
          number: 5,
          icon: Home,
          text: "Spore apparaît maintenant sur votre écran d'accueil.",
        },
      ],
    },
    {
      id: 'chrome-ios',
      title: 'Avec Google Chrome',
      icon: Globe,
      steps: [
        {
          id: 'chrome-ios-1',
          icon: Share,
          text: "Appuyez sur le bouton Partager, à droite de la barre d'adresse.",
        },
        {
          id: 'chrome-ios-2',
          icon: Plus,
          text: "Sélectionnez Ajouter à l'écran d'accueil.",
        },
        {
          id: 'chrome-ios-3',
          icon: Check,
          text: 'Appuyez sur Ajouter. Spore apparaît maintenant parmi vos applications.',
        },
      ],
    },
    {
      id: 'other-ios',
      title: 'Avec un autre navigateur',
      steps: [
        {
          id: 'other-ios-1',
          icon: Share,
          text: "Recherchez le bouton Partager, puis sélectionnez Ajouter à l'écran d'accueil.",
        },
        {
          id: 'other-ios-2',
          icon: Settings,
          text: 'Si cette option n\'apparaît pas, ouvrez cette page dans Safari ou Google Chrome, puis recommencez.',
        },
      ],
    },
  ],
  android: [
    {
      id: 'chrome-android',
      title: 'Avec Google Chrome',
      icon: Globe,
      footnote:
        "Selon votre téléphone et la version de Chrome, l'option peut également s'appeler Installer l'application.",
      steps: [
        {
          id: 'chrome-android-1',
          number: 1,
          icon: Check,
          text: 'Une fenêtre d\'installation peut apparaître automatiquement. Dans ce cas, appuyez simplement sur Installer.',
        },
        {
          id: 'chrome-android-2',
          number: 2,
          icon: MoreVertical,
          text: 'Sinon, appuyez sur le menu ⋮ en haut à droite.',
        },
        {
          id: 'chrome-android-3',
          number: 3,
          icon: Plus,
          text: "Sélectionnez Ajouter à l'écran d'accueil.",
        },
        {
          id: 'chrome-android-4',
          number: 4,
          icon: Check,
          text: "Appuyez sur Installer, puis confirmez l'installation.",
        },
      ],
    },
    {
      id: 'samsung-internet',
      title: 'Avec Samsung Internet',
      icon: Smartphone,
      steps: [
        {
          id: 'samsung-1',
          icon: Menu,
          text: 'Appuyez sur le menu ☰ en bas de l\'écran.',
        },
        {
          id: 'samsung-2',
          icon: Plus,
          text: "Sélectionnez Ajouter la page à, puis choisissez Écran d'accueil.",
        },
        {
          id: 'samsung-3',
          icon: Check,
          text: "Confirmez l'ajout. Une icône + peut également apparaître directement dans la barre du navigateur.",
        },
      ],
    },
    {
      id: 'firefox',
      title: 'Avec Firefox',
      icon: Globe,
      steps: [
        {
          id: 'firefox-1',
          icon: MoreVertical,
          text: 'Appuyez sur le menu ⋮.',
        },
        {
          id: 'firefox-2',
          icon: Check,
          text: "Sélectionnez Installer, puis appuyez sur Ajouter automatiquement ou choisissez l'emplacement de l'icône.",
        },
      ],
    },
    {
      id: 'other-android',
      title: 'Avec Edge, Brave ou un autre navigateur',
      steps: [
        {
          id: 'other-android-1',
          icon: MoreVertical,
          text: 'Ouvrez le menu du navigateur.',
        },
        {
          id: 'other-android-2',
          icon: Check,
          text: "Recherchez Installer l'application ou Ajouter à l'écran d'accueil, puis confirmez l'installation.",
        },
      ],
    },
  ],
}

export const INSTALL_PLATFORM_TABS: Array<{
  value: InstallPlatform
  label: string
  icon: LucideIcon
}> = [
  { value: 'ios', label: 'iOS / iPad', icon: Apple },
  { value: 'android', label: 'Android', icon: Smartphone },
]

export const INSTALL_APP_HERO_ICON = MonitorSmartphone
